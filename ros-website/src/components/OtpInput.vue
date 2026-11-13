<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    disabled?: boolean;
    autoFocus?: boolean;
  }>(),
  {
    modelValue: '',
    disabled: false,
    autoFocus: true
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'complete', value: string): void;
}>();

const digits = ref<string[]>(['', '', '', '', '', '']);
const inputRefs = ref<(HTMLInputElement | null)[]>([]);

watch(
  () => props.modelValue,
  (newVal) => {
    if (!newVal) {
      digits.value = ['', '', '', '', '', ''];
      return;
    }
    const chars = newVal.slice(0, 6).split('');
    digits.value = [
      chars[0] || '',
      chars[1] || '',
      chars[2] || '',
      chars[3] || '',
      chars[4] || '',
      chars[5] || ''
    ];
  },
  { immediate: true }
);

onMounted(() => {
  if (props.autoFocus && inputRefs.value[0]) {
    inputRefs.value[0].focus();
  }
});

function syncValue() {
  const full = digits.value.join('');
  emit('update:modelValue', full);
  if (full.length === 6 && /^[0-9]{6}$/.test(full)) {
    emit('complete', full);
  }
}

function onInput(index: number, e: Event) {
  const target = e.target as HTMLInputElement;
  const val = target.value.replace(/[^0-9]/g, '');

  if (val.length > 0) {
    digits.value[index] = val[val.length - 1]; // take the latest digit
    syncValue();
    if (index < 5 && inputRefs.value[index + 1]) {
      inputRefs.value[index + 1]?.focus();
    }
  } else {
    digits.value[index] = '';
    syncValue();
  }
}

function onKeyDown(index: number, e: KeyboardEvent) {
  if (e.key === 'Backspace') {
    if (digits.value[index] === '' && index > 0) {
      digits.value[index - 1] = '';
      syncValue();
      inputRefs.value[index - 1]?.focus();
    } else {
      digits.value[index] = '';
      syncValue();
    }
  } else if (e.key === 'ArrowLeft' && index > 0) {
    inputRefs.value[index - 1]?.focus();
  } else if (e.key === 'ArrowRight' && index < 5) {
    inputRefs.value[index + 1]?.focus();
  }
}

function onPaste(e: ClipboardEvent) {
  e.preventDefault();
  const pasteData = e.clipboardData?.getData('text') || '';
  const cleanDigits = pasteData.replace(/[^0-9]/g, '').slice(0, 6);
  if (!cleanDigits) return;

  for (let i = 0; i < 6; i++) {
    digits.value[i] = cleanDigits[i] || '';
  }
  syncValue();

  nextTick(() => {
    const nextIdx = Math.min(cleanDigits.length, 5);
    inputRefs.value[nextIdx]?.focus();
  });
}
</script>

<template>
  <div class="otp-container" @paste="onPaste">
    <div class="otp-inputs">
      <input
        v-for="(digit, idx) in digits"
        :key="idx"
        :ref="(el) => (inputRefs[idx] = el as HTMLInputElement)"
        type="text"
        inputmode="numeric"
        maxlength="1"
        autocomplete="one-time-code"
        :value="digit"
        :disabled="disabled"
        class="otp-box"
        :aria-label="`Verification code digit ${idx + 1}`"
        @input="onInput(idx, $event)"
        @keydown="onKeyDown(idx, $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.otp-container {
  display: flex;
  justify-content: center;
  margin: 1.25rem 0;
}

.otp-inputs {
  display: flex;
  gap: 0.6rem;
}

.otp-box {
  width: 48px;
  height: 56px;
  text-align: center;
  font-size: 1.5rem;
  font-weight: 800;
  font-family: var(--font-mono);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--accent-gold);
  border-radius: 6px;
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.otp-box:focus {
  border-color: var(--accent-gold);
  background-color: var(--bg-card);
  box-shadow: 0 0 0 3px rgba(215, 168, 75, 0.25);
  transform: translateY(-2px);
}

.otp-box:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 400px) {
  .otp-box {
    width: 40px;
    height: 48px;
    font-size: 1.25rem;
  }
  .otp-inputs {
    gap: 0.4rem;
  }
}
</style>
