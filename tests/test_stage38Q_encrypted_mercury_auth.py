
import unittest, socket, struct, tempfile, shutil, os, time, json
from phase6B_25_diamond_economy.src.diamond_economy_db import DiamondEconomyDatabase
from phase6B_27_player_auth.src.account_manager import AccountManager
from phase6B_27_player_auth.src.session_manager import SessionManager
from phase6B_27_player_auth.src.mercury_login_service import MercuryLoginService
from phase6B_24_original_login_compatibility.src.login_packet_codec import LogOnParams, LoginReply
from phase6B_24_original_login_compatibility.src.rsa_crypto import RsaPublicKey, RsaPrivateKey, parse_rsa_public_key_pem

class TestEncryptedNativeMercuryAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix='ros_enc_auth_')
        cls.test_db = os.path.join(cls.temp_dir, 'test.db')
        shutil.copy2('phase6B_25_diamond_economy/data/diamond_economy.db', cls.test_db)
        
        cls.acct_mgr = AccountManager(cls.test_db)
        cls.sess_mgr = SessionManager(cls.acct_mgr.conn, cls.acct_mgr._lock)
        
        # Load keys
        with open('phase6B_27_player_auth/data/keys/loginapp_privkey.json') as f:
            priv_json = json.load(f)
        cls.priv = RsaPrivateKey(priv_json['n'], priv_json['e'], priv_json['d'])
        with open('phase6B_27_player_auth/data/keys/loginapp.pubkey') as f:
            cls.pub = parse_rsa_public_key_pem(f.read())
            
        cls.test_user = 'synth_enc_player'
        cls.test_pass = 'Secret#P@ssword2026'
        cls.acct_mgr.register_account(cls.test_user, cls.test_pass)
        
        cls.port = 29995
        cls.service = MercuryLoginService(cls.acct_mgr, cls.sess_mgr, host='127.0.0.1', port=cls.port, priv_key=cls.priv)
        cls.service.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.service.stop()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_public_private_key_pair_match(self):
        self.assertEqual(self.pub.n, self.priv.n)
        self.assertEqual(self.pub.e, self.priv.e)
        self.assertEqual(self.pub.size_bytes, 128)
        self.assertEqual(self.priv.size_bytes, 128)

    def test_02_encrypted_request_decrypts_correctly(self):
        params = LogOnParams('test_user_codec', 'secret_pass_codec')
        wire_enc = params.encode_encrypted(self.pub)
        self.assertEqual(len(wire_enc), 129)
        self.assertEqual(wire_enc[0], 0x80)
        
        decoded = LogOnParams.decode_encrypted(wire_enc, self.priv)
        self.assertEqual(decoded.username, 'test_user_codec')
        self.assertEqual(decoded.password, 'secret_pass_codec')

    def test_03_valid_account_authentication_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        params = LogOnParams(self.test_user, self.test_pass)
        enc_bytes = params.encode_encrypted(self.pub)
        sock.sendto(enc_bytes, ('127.0.0.1', self.port))
        resp, _ = sock.recvfrom(4096)
        sock.close()
        
        reply = LoginReply.decode(resp)
        self.assertEqual(reply.status, 0)
        self.assertEqual(reply.baseapp_port, 20014)
        self.assertGreater(reply.session_key, 0)

    def test_04_invalid_password_rejected(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        params = LogOnParams(self.test_user, 'WrongPassword#999')
        enc_bytes = params.encode_encrypted(self.pub)
        sock.sendto(enc_bytes, ('127.0.0.1', self.port))
        resp, _ = sock.recvfrom(4096)
        sock.close()
        
        reply = LoginReply.decode(resp)
        self.assertEqual(reply.status, 2)
        self.assertIn('Invalid', reply.error_message)

    def test_05_unknown_username_rejected(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        params = LogOnParams('unknown_player_xyz_8888', 'any_pass')
        enc_bytes = params.encode_encrypted(self.pub)
        sock.sendto(enc_bytes, ('127.0.0.1', self.port))
        resp, _ = sock.recvfrom(4096)
        sock.close()
        
        reply = LoginReply.decode(resp)
        self.assertEqual(reply.status, 1)
        self.assertIn('exist', reply.error_message)

    def test_06_udp_encrypted_authentication(self):
        # Register second user to avoid 30s replay cache
        u = 'udp_player_77'
        p = 'UdpPass#2026'
        self.acct_mgr.register_account(u, p)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        params = LogOnParams(u, p)
        enc_bytes = params.encode_encrypted(self.pub)
        sock.sendto(enc_bytes, ('127.0.0.1', self.port))
        resp, _ = sock.recvfrom(4096)
        sock.close()
        
        reply = LoginReply.decode(resp)
        self.assertEqual(reply.status, 0)

    def test_07_tcp_fallback_encrypted_authentication(self):
        u = 'tcp_player_88'
        p = 'TcpPass#2026'
        self.acct_mgr.register_account(u, p)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(('127.0.0.1', self.port))
        params = LogOnParams(u, p)
        enc_bytes = params.encode_encrypted(self.pub)
        tcp_req = struct.pack('!H', len(enc_bytes)) + enc_bytes
        sock.sendall(tcp_req)
        
        hdr = sock.recv(2)
        resp_len = struct.unpack('!H', hdr)[0]
        resp_bytes = sock.recv(resp_len)
        sock.close()
        
        reply = LoginReply.decode(resp_bytes)
        self.assertEqual(reply.status, 0)

    def test_08_oversized_credentials_fail_safely(self):
        # Username 60 + Password 60 = 120 bytes > 117 bytes limit
        oversized_u = 'a' * 60
        oversized_p = 'b' * 60
        params = LogOnParams(oversized_u, oversized_p)
        with self.assertRaises(Exception):
            params.encode_encrypted(self.pub)

    def test_09_packet_inspection_no_plaintext_leakage(self):
        secret_u = 'super_secret_username_99'
        secret_p = 'MySecretPassphrase#2026'
        params = LogOnParams(secret_u, secret_p)
        wire_data = params.encode_encrypted(self.pub)
        
        # Verify plaintext strings cannot be found anywhere in the wire bytes
        self.assertNotIn(secret_u.encode('utf-8'), wire_data)
        self.assertNotIn(secret_p.encode('utf-8'), wire_data)
        # Verify wire data length is exactly 129 bytes (0x80 + 128 ciphertext)
        self.assertEqual(len(wire_data), 129)

    def test_10_no_http_fallback_in_auth_client(self):
        with open('src/hook/src/auth_client.m', 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertNotIn('NSURLSession', src)
        self.assertNotIn('postJSON', src)
        self.assertIn('SecKeyCreateEncryptedData', src)
        self.assertIn('encrypt_logon_params', src)
        self.assertIn('Aborting login without sending plaintext', src)

suite = unittest.TestLoader().loadTestsFromTestCase(TestEncryptedNativeMercuryAuth)
runner = unittest.TextTestRunner(verbosity=2)
res = runner.run(suite)
assert res.wasSuccessful()
print('=== ALL 10 PHASE 4 TESTS PASSED SUCCESSFULLY ===')
