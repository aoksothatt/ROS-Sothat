"""
ROS Sothatt — Stage 38Q Fishhook Safety & Memory Protection Test Suite.

Verifies:
1. Callback signature correctness:
   - _rebind_symbols_for_image takes exactly (const struct mach_header *, intptr_t).
   - _dyld_register_func_for_add_image is called with _rebind_symbols_for_image directly without casting.
   - Global _rebindings_head is forwarded as parameter 1 to rebind_symbols_for_image.
2. get_protection section target:
   - get_protection is passed indirect_symbol_bindings (the Mach-O section pointer).
   - Never passed heap pointer rebindings.
3. Section bounds and null checks:
   - perform_rebinding_with_section checks for null section and zero size.
   - Page alignment arithmetic correctly aligns addresses to 16KB iOS boundary (0x4000)
     and calculates enclosing size across single and multi-page spans.
4. vm_protect error handling and iOS 16 __DATA_CONST:
   - Uses vm_protect with VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY.
   - Validates return value against KERN_SUCCESS and aborts safely if protection fails.
   - Eliminates unaligned mprotect on __DATA_CONST.
5. Restoration of original protections:
   - Restores oldProtection via vm_protect across aligned address range.
6. Existing socket redirection hooks preserved:
   - sendto and recvfrom hooks in rossothat_install_socket_hooks.
   - connect hook in rossothat_install_connect_hook targeting discovery service.
"""

import os
import re
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FISHHOOK_C = os.path.join(PROJECT_ROOT, "src", "hook", "src", "fishhook.c")
BASEAPP_HOOK_C = os.path.join(PROJECT_ROOT, "src", "hook", "src", "baseapp_hook.c")
HOOK_MAIN_M = os.path.join(PROJECT_ROOT, "src", "hook", "src", "rossothathook.m")


class TestFishhookSafety(unittest.TestCase):
    """Safety and memory-protection verification suite for fishhook on iOS 16."""

    @classmethod
    def setUpClass(cls):
        with open(FISHHOOK_C, "r", encoding="utf-8") as f:
            cls.fishhook_src = f.read()
        with open(BASEAPP_HOOK_C, "r", encoding="utf-8") as f:
            cls.baseapp_hook_src = f.read()

    def test_01_callback_signature_correctness(self):
        """Verifies 2-argument wrapper matches dyld calling convention without casts."""
        # 1. Helper function definition exists with exact 2-argument signature
        wrapper_pattern = (
            r"static\s+void\s+_rebind_symbols_for_image\s*\(\s*"
            r"const\s+struct\s+mach_header\s*\*\s*header\s*,\s*"
            r"intptr_t\s+slide\s*\)\s*\{"
        )
        self.assertRegex(self.fishhook_src, wrapper_pattern,
                         "_rebind_symbols_for_image must take (const struct mach_header *, intptr_t)")

        # 2. Wrapper forwards _rebindings_head as first argument
        forward_call = "rebind_symbols_for_image(_rebindings_head, header, slide);"
        self.assertIn(forward_call, self.fishhook_src,
                      "_rebind_symbols_for_image must pass _rebindings_head to rebind_symbols_for_image")

        # 3. Registration with dyld uses wrapper with NO function pointer cast
        dyld_reg = "_dyld_register_func_for_add_image(_rebind_symbols_for_image);"
        self.assertIn(dyld_reg, self.fishhook_src,
                      "_dyld_register_func_for_add_image must register _rebind_symbols_for_image directly without casting")

        # 4. Old cast pattern must be completely eliminated
        self.assertNotIn("(void (*)(const struct mach_header *, intptr_t))rebind_symbols_for_image",
                         self.fishhook_src,
                         "Unsafe 3-argument cast to dyld registration must be removed")

    def test_02_get_protection_section_target(self):
        """Verifies get_protection queries section memory instead of heap entry."""
        # 1. get_protection receives indirect_symbol_bindings and aligned region bounds
        correct_call = "if (!get_protection(indirect_symbol_bindings, aligned_addr, aligned_size, &oldProtection))"
        self.assertIn(correct_call, self.fishhook_src,
                      "get_protection must be passed indirect_symbol_bindings, aligned bounds, and output pointer")

        # 2. Defective get_protection(rebindings) must not exist
        self.assertNotIn("get_protection(rebindings", self.fishhook_src,
                         "get_protection(rebindings) queried heap memory and must be eliminated")

        # 3. Function definition returns bool and accepts sectionStart, bounds, and output pointer
        proto_pattern = (
            r"static\s+bool\s+get_protection\s*\(\s*void\s*\*sectionStart\s*,\s*"
            r"vm_address_t\s+aligned_addr\s*,\s*vm_size_t\s+aligned_size\s*,\s*"
            r"vm_prot_t\s*\*protection\s*\)"
        )
        self.assertRegex(self.fishhook_src, proto_pattern,
                         "get_protection must return bool and receive sectionStart, aligned_addr, aligned_size, and protection")

    def test_03_section_bounds_and_null_checks(self):
        """Verifies perform_rebinding_with_section checks bounds and null pointers."""
        # 1. Null section and zero size check
        self.assertIn("if (!section || section->size == 0)", self.fishhook_src,
                      "perform_rebinding_with_section must guard against null sections and zero size")

        # 2. Mathematical simulation of page alignment logic on 16KB iOS boundary
        page_size = 16384
        page_mask = page_size - 1

        test_cases = [
            # (start_addr, section_size, expected_aligned_addr, expected_aligned_size)
            (0x100004000, 0x100, 0x100004000, 0x4000),      # Already page-aligned
            (0x100004080, 0x200, 0x100004000, 0x4000),      # Unaligned start, single page
            (0x100007F00, 0x300, 0x100004000, 0x8000),      # Straddling across page boundary
            (0x100004080, 0x4000, 0x100004000, 0x8000),     # Exact page size but unaligned
            (0x100004000, 0x4000, 0x100004000, 0x4000),     # Exact page size and aligned
        ]

        for addr, size, exp_aligned_addr, exp_aligned_size in test_cases:
            aligned_addr = addr & ~page_mask
            aligned_size = (((addr + size + page_mask) & ~page_mask) - aligned_addr)

            # Assert page boundary alignment
            self.assertEqual(aligned_addr % page_size, 0, f"Aligned address 0x{aligned_addr:X} not page-aligned")
            self.assertEqual(aligned_size % page_size, 0, f"Aligned size 0x{aligned_size:X} not page-multiple")

            # Assert exact expected calculation
            self.assertEqual(aligned_addr, exp_aligned_addr)
            self.assertEqual(aligned_size, exp_aligned_size)

            # Assert that the aligned region completely encloses [addr, addr + size)
            self.assertLessEqual(aligned_addr, addr)
            self.assertGreaterEqual(aligned_addr + aligned_size, addr + size)

    def test_04_vm_protect_and_memory_protection_failures(self):
        """Verifies vm_protect with VM_PROT_COPY and safe failure aborts."""
        # 1. vm_protect uses VM_PROT_COPY for iOS 16 __DATA_CONST
        self.assertIn("VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY", self.fishhook_src,
                      "vm_protect must request VM_PROT_COPY for iOS 15/16 copy-on-write mappings")

        # 2. Return value checked against KERN_SUCCESS
        err_check_pattern = (
            r"kern_return_t\s+err\s*=\s*vm_protect\s*\([\s\S]+?\);\s*"
            r"if\s*\(\s*err\s*!=\s*KERN_SUCCESS\s*\)\s*\{\s*return;\s*\}"
        )
        self.assertRegex(self.fishhook_src, err_check_pattern,
                         "vm_protect return value must be checked and safely return on failure")

        # 3. No unaligned mprotect on __DATA_CONST
        self.assertNotIn("mprotect(indirect_symbol_bindings", self.fishhook_src,
                         "POSIX mprotect on indirect_symbol_bindings must be eliminated")

    def test_05_restoration_of_original_protections(self):
        """Verifies original protection is restored using vm_protect."""
        # 1. Restoration call uses oldProtection directly
        restore_pattern = (
            r"vm_protect\s*\(\s*mach_task_self\s*\(\s*\)\s*,\s*"
            r"aligned_addr\s*,\s*aligned_size\s*,\s*false\s*,\s*oldProtection\s*\)"
        )
        self.assertRegex(self.fishhook_src, restore_pattern,
                         "vm_protect must restore oldProtection across aligned page region")

    def test_06_socket_redirection_hooks_preserved(self):
        """Ensures socket hooks architecture and target redirection remain intact."""
        # 1. BaseApp hooks for sendto and recvfrom
        self.assertIn('{"sendto", sothat_hook_sendto, (void **)&orig_sendto}', self.baseapp_hook_src)
        self.assertIn('{"recvfrom", sothat_hook_recvfrom, (void **)&orig_recvfrom}', self.baseapp_hook_src)
        self.assertIn('rossothat_install_socket_hooks', self.baseapp_hook_src)

        # 2. Connect hook for discovery HTTPS redirection
        self.assertIn('{"connect", sothat_hook_connect, (void **)&orig_connect}', self.baseapp_hook_src)
        self.assertIn('rossothat_install_connect_hook', self.baseapp_hook_src)
        self.assertIn('172.65.54.209', self.baseapp_hook_src)
        self.assertIn('50443', self.baseapp_hook_src)

    def test_07_overflow_guard_before_alignment(self):
        """Verifies integer overflow guard protects section range calculations."""
        # 1. Source check: overflow guard exists before aligned_addr / aligned_size
        overflow_pattern = (
            r"if\s*\(\s*raw_addr\s*\+\s*section->size\s*<\s*raw_addr\s*\|\|\s*"
            r"\(\s*raw_addr\s*\+\s*section->size\s*\+\s*page_mask\s*\)\s*<\s*"
            r"\(\s*raw_addr\s*\+\s*section->size\s*\)\s*\)\s*\{\s*return;\s*\}"
        )
        self.assertRegex(self.fishhook_src, overflow_pattern,
                         "Overflow guard must abort if raw_addr + size or + page_mask wraps around")

        # 2. Mathematical simulation of 64-bit unsigned integer wrap-around
        MASK_64 = 0xFFFFFFFFFFFFFFFF
        page_mask = 16383

        def check_overflow(addr, size):
            sum1 = (addr + size) & MASK_64
            if sum1 < addr:
                return True
            sum2 = (sum1 + page_mask) & MASK_64
            if sum2 < sum1:
                return True
            return False

        # Normal valid range: must not trigger overflow
        self.assertFalse(check_overflow(0x100004000, 0x1000))
        self.assertFalse(check_overflow(0x200000000, 0x8000))

        # Extreme values that wrap 64-bit boundary: must trigger overflow
        self.assertTrue(check_overflow(0xFFFFFFFFFFFFFF00, 0x200))
        self.assertTrue(check_overflow(0xFFFFFFFFFFFFC000, 0x4000))
        self.assertTrue(check_overflow(MASK_64, 1))

    def test_08_restoration_error_handling_explicit(self):
        """Verifies restoration error is explicitly handled and reported via direct write without stdio."""
        # 1. rest_err checked against KERN_SUCCESS
        rest_check = "if (rest_err != KERN_SUCCESS)"
        self.assertIn(rest_check, self.fishhook_src,
                      "rest_err must be explicitly checked against KERN_SUCCESS")

        # 2. Discarding (void)rest_err; must be eliminated
        self.assertNotIn("(void)rest_err;", self.fishhook_src,
                         "(void)rest_err; must be eliminated")

        # 3. Minimal direct write(STDERR_FILENO, ...) message used
        self.assertIn("write(STDERR_FILENO, warn_msg, sizeof(warn_msg) - 1);", self.fishhook_src,
                      "Failure to restore protection must be reported via direct write(STDERR_FILENO, ...)")
        self.assertIn("<unistd.h>", self.fishhook_src,
                      "<unistd.h> must be included for direct write")

        # 4. stdio.h, fprintf, and snprintf must NOT be present
        self.assertNotIn("<stdio.h>", self.fishhook_src,
                         "stdio.h must be eliminated from fishhook.c")
        self.assertNotIn("fprintf(", self.fishhook_src,
                         "fprintf must be eliminated to avoid stdio stream locking during dyld callbacks")
        self.assertNotIn("snprintf(", self.fishhook_src,
                         "snprintf must be eliminated to ensure zero formatting overhead")

        # 5. Safe failure behavior preserved: no unsafe exit() or abort()
        self.assertNotIn("exit(", self.fishhook_src)
        self.assertNotIn("abort()", self.fishhook_src)

    def test_09_binding_addr_overflow_guard(self):
        """Verifies slide + section->addr overflow is guarded before computing raw_addr."""
        # 1. Source check: binding_addr calculation and overflow check exist
        self.assertIn("uintptr_t binding_addr = (uintptr_t)slide + (uintptr_t)section->addr;", self.fishhook_src)
        self.assertIn("if (binding_addr < (uintptr_t)slide)", self.fishhook_src)
        self.assertIn("if (binding_addr > (uintptr_t)section->addr)", self.fishhook_src)
        self.assertIn("if (binding_addr == 0)", self.fishhook_src)

        # 2. Mathematical simulation of slide + section->addr overflow
        MASK_64 = 0xFFFFFFFFFFFFFFFF

        def check_binding_overflow(slide_val, sect_addr):
            # simulate 64-bit unsigned addition
            b_addr = (slide_val + sect_addr) & MASK_64
            if slide_val >= 0:
                if b_addr < slide_val:
                    return True
            else:
                if b_addr > sect_addr:
                    return True
            return b_addr == 0

        # Normal valid positive slide (ASLR)
        self.assertFalse(check_binding_overflow(0x4000000, 0x100004080))
        # Zero slide
        self.assertFalse(check_binding_overflow(0, 0x100004080))
        # Extreme positive overflow wrapping 64-bit
        self.assertTrue(check_binding_overflow(0x8000000000000000, 0x8000000000001000))
        self.assertTrue(check_binding_overflow(MASK_64, 1))

    def test_10_page_size_power_of_two_validation(self):
        """Verifies page_size is validated as a nonzero power of two before mask calculation."""
        # 1. Source check: power of two check exists
        self.assertIn("if (page_size == 0 || (page_size & (page_size - 1)) != 0)", self.fishhook_src)
        self.assertIn("page_size = 16384;", self.fishhook_src)

        # 2. Logic simulation
        def sanitize_page_size(val):
            ps = val
            if ps == 0 or (ps & (ps - 1)) != 0:
                ps = 16384
            return ps, ps - 1

        # Valid power of two page sizes
        self.assertEqual(sanitize_page_size(16384), (16384, 0x3FFF))
        self.assertEqual(sanitize_page_size(4096), (4096, 0x0FFF))

        # Invalid: 0
        self.assertEqual(sanitize_page_size(0), (16384, 0x3FFF))
        # Invalid: non-power of two
        self.assertEqual(sanitize_page_size(16385), (16384, 0x3FFF))
        self.assertEqual(sanitize_page_size(12000), (16384, 0x3FFF))

    def test_11_get_protection_failure_handling(self):
        """Verifies protection discovery failure safely aborts without modifying memory."""
        # 1. On discovery failure, perform_rebinding_with_section aborts before vm_protect
        abort_pattern = (
            r"if\s*\(\s*!get_protection\s*\(\s*indirect_symbol_bindings\s*,\s*aligned_addr\s*,\s*aligned_size\s*,\s*&oldProtection\s*\)\s*\)\s*\{\s*"
            r"return;\s*"
            r"\}"
        )
        self.assertRegex(self.fishhook_src, abort_pattern,
                         "perform_rebinding_with_section must abort if get_protection returns false")

        # 2. Never guess original protection on failure
        self.assertNotIn("return VM_PROT_READ;", self.fishhook_src,
                         "get_protection must never return VM_PROT_READ as a guessed fallback on error")

        # 3. Parameter validation inside get_protection
        self.assertIn("if (!sectionStart || !protection || aligned_size == 0)", self.fishhook_src)
        self.assertIn("if (sec_addr < aligned_addr || sec_addr >= (aligned_addr + aligned_size))", self.fishhook_src)

    def test_12_vm_region_complete_range_coverage(self):
        """Verifies that the discovered VM region covers the complete aligned memory range."""
        # 1. Source check: region boundary checks exist in get_protection
        self.assertIn("if (address > aligned_addr)", self.fishhook_src,
                      "Must verify region starts at or before aligned_addr")
        self.assertIn("if ((address + size) < address)", self.fishhook_src,
                      "Must guard against region size integer overflow")
        self.assertIn("if ((aligned_addr + aligned_size) > (address + size))", self.fishhook_src,
                      "Must verify region completely encloses the aligned range")

        # 2. Mathematical logic simulation of VM region coverage
        MASK_64 = 0xFFFFFFFFFFFFFFFF

        def is_region_valid_and_covering(reg_start, reg_size, target_addr, target_size):
            if reg_start > target_addr:
                return False  # Target start is not inside region (unmapped space skipped)
            reg_end = (reg_start + reg_size) & MASK_64
            if reg_end < reg_start:
                return False  # Region address arithmetic overflow
            target_end = (target_addr + target_size) & MASK_64
            if target_end > reg_end:
                return False  # Target extends past region end (cross-region or truncated)
            return True

        # Valid scenarios:
        # Region exactly matches target range
        self.assertTrue(is_region_valid_and_covering(0x100004000, 0x4000, 0x100004000, 0x4000))
        # Region generously encloses target range
        self.assertTrue(is_region_valid_and_covering(0x100000000, 0x100000, 0x100004000, 0x8000))

        # Invalid scenarios:
        # Region starts after target address (e.g. unmapped gap)
        self.assertFalse(is_region_valid_and_covering(0x100008000, 0x4000, 0x100004000, 0x4000))
        # Region ends before target range ends (spanning multiple regions)
        self.assertFalse(is_region_valid_and_covering(0x100004000, 0x4000, 0x100004000, 0x8000))
        # Region size overflows 64-bit boundary
        self.assertFalse(is_region_valid_and_covering(0xFFFFFFFFFFFF0000, 0x20000, 0xFFFFFFFFFFFF0000, 0x4000))

    def test_13_mach_port_cleanup(self):
        """Verifies Mach port returned by vm_region_64 is properly deallocated."""
        # 1. Mach port check and deallocation call exists
        cleanup_pattern = (
            r"if\s*\(\s*object\s*!=\s*MACH_PORT_NULL\s*&&\s*object\s*!=\s*MACH_PORT_DEAD\s*\)\s*\{\s*"
            r"mach_port_deallocate\s*\(\s*task\s*,\s*object\s*\);\s*"
            r"\}"
        )
        self.assertRegex(self.fishhook_src, cleanup_pattern,
                         "Mach port returned by vm_region_64 must be deallocated via mach_port_deallocate")

    def test_14_aligned_range_overflow_guard(self):
        """Verifies aligned_addr + aligned_size cannot overflow before being used in comparisons."""
        # 1. Source check: explicit overflow guard in get_protection
        self.assertIn("if (aligned_addr + aligned_size < aligned_addr)", self.fishhook_src,
                      "get_protection must check aligned_addr + aligned_size < aligned_addr before comparisons")

        # 2. Mathematical simulation of addition overflow
        MASK_64 = 0xFFFFFFFFFFFFFFFF

        def check_aligned_overflow(addr, size):
            end = (addr + size) & MASK_64
            return end < addr

        # Valid non-overflowing ranges
        self.assertFalse(check_aligned_overflow(0x100004000, 0x4000))
        self.assertFalse(check_aligned_overflow(0x200000000, 0x10000))

        # Extreme values that overflow 64-bit vm_address_t
        self.assertTrue(check_aligned_overflow(0xFFFFFFFFFFFFC000, 0x8000))
        self.assertTrue(check_aligned_overflow(MASK_64, 1))
        self.assertTrue(check_aligned_overflow(0xFFFFFFFFFFFFFFFF, 0x4000))

    def test_15_shared_cache_image_filtering(self):
        """Verifies MH_DYLIB_IN_CACHE is defined and shared-cache images are safely skipped."""
        # 1. MH_DYLIB_IN_CACHE defined with safe guard
        self.assertIn("#ifndef MH_DYLIB_IN_CACHE", self.fishhook_src)
        self.assertIn("#define MH_DYLIB_IN_CACHE 0x80000000", self.fishhook_src)

        # 2. rebind_symbols_for_image checks header->flags & MH_DYLIB_IN_CACHE and aborts
        cache_guard = (
            r"if\s*\(\s*header->flags\s*&\s*MH_DYLIB_IN_CACHE\s*\)\s*\{\s*"
            r"return;\s*"
            r"\}"
        )
        self.assertRegex(self.fishhook_src, cache_guard,
                         "rebind_symbols_for_image must skip images with MH_DYLIB_IN_CACHE flag")

        # 3. Simulation of shared cache vs standalone Mach-O headers
        MH_DYLIB_IN_CACHE = 0x80000000
        client_flags = 0x218085          # Standalone client executable
        rosauthhook_flags = 0x100085     # Standalone rosauthhook.dylib
        libsystem_flags = 0x80000085     # Cached system dylib in iOS shared cache

        def is_shared_cache_image(flags):
            return bool(flags & MH_DYLIB_IN_CACHE)

        self.assertFalse(is_shared_cache_image(client_flags), "App client must not be flagged as shared cache")
        self.assertFalse(is_shared_cache_image(rosauthhook_flags), "Hook dylib must not be flagged as shared cache")
        self.assertTrue(is_shared_cache_image(libsystem_flags), "System dylib must be flagged as shared cache")

    def test_16_supported_macho_image_types(self):
        """Verifies rebind_symbols_for_image processes only MH_EXECUTE and MH_DYLIB."""
        type_guard = (
            r"if\s*\(\s*header->filetype\s*!=\s*MH_EXECUTE\s*&&\s*header->filetype\s*!=\s*MH_DYLIB\s*\)\s*\{\s*"
            r"return;\s*"
            r"\}"
        )
        self.assertRegex(self.fishhook_src, type_guard,
                         "rebind_symbols_for_image must only process MH_EXECUTE and MH_DYLIB")

        MH_EXECUTE = 2
        MH_DYLIB = 6
        MH_OBJECT = 1
        MH_BUNDLE = 8

        def is_supported_type(filetype):
            return filetype == MH_EXECUTE or filetype == MH_DYLIB

        self.assertTrue(is_supported_type(MH_EXECUTE))
        self.assertTrue(is_supported_type(MH_DYLIB))
        self.assertFalse(is_supported_type(MH_OBJECT))
        self.assertFalse(is_supported_type(MH_BUNDLE))

    def test_17_indirect_symbol_indices_and_symtab_bounds_checks(self):
        """Verifies bounds checks on section->reserved1, nindirectsyms, and symtab_index."""
        # 1. Null check and zero size checks on tables in perform_rebinding_with_section
        self.assertIn("if (!symtab || !strtab || !indirect_symtab || nsyms == 0 || strsize == 0 || nindirectsyms == 0)",
                      self.fishhook_src)
        self.assertIn("if (section->reserved1 >= nindirectsyms)", self.fishhook_src)

        # 2. entries bounds clamp against available indirect symbol indices
        self.assertIn("uint32_t available_indices = nindirectsyms - section->reserved1;", self.fishhook_src)
        self.assertIn("if (entries > available_indices)", self.fishhook_src)

        # 3. symtab_index checked against nsyms before indexing symtab
        self.assertIn("if (symtab_index >= nsyms)", self.fishhook_src)

        # 4. Simulation of bounds check
        def validate_symtab_access(nindirectsyms, reserved1, section_size, ptr_size, symtab_index, nsyms):
            if reserved1 >= nindirectsyms:
                return False
            entries = section_size // ptr_size
            available = nindirectsyms - reserved1
            if entries > available:
                entries = available
            if symtab_index >= nsyms:
                return False
            return True

        self.assertTrue(validate_symtab_access(4290, 1575, 0x23a0, 8, 100, 2731))
        # Out-of-bounds reserved1
        self.assertFalse(validate_symtab_access(100, 150, 0x100, 8, 10, 200))
        # Out-of-bounds symtab_index
        self.assertFalse(validate_symtab_access(4290, 1575, 0x23a0, 8, 3000, 2731))

    def test_18_strtab_offset_and_string_length_bounds_checks(self):
        """Verifies strtab_offset is bounds-checked against strsize before dereferencing."""
        self.assertIn("if (strtab_offset >= strsize || (strsize - strtab_offset) < 2)", self.fishhook_src,
                      "strtab_offset must be verified within strsize and have at least 2 bytes for symbol_name[0] and [1]")

        def is_safe_string_read(strsize, offset):
            if offset >= strsize or (strsize - offset) < 2:
                return False
            return True

        # Valid offsets
        self.assertTrue(is_safe_string_read(1000, 50))
        self.assertTrue(is_safe_string_read(1000, 998))
        # Invalid offsets (out of bounds or insufficient length for symbol_name[0] and symbol_name[1])
        self.assertFalse(is_safe_string_read(1000, 999))
        self.assertFalse(is_safe_string_read(1000, 1000))
        self.assertFalse(is_safe_string_read(1000, 5000))


if __name__ == "__main__":
    unittest.main()
