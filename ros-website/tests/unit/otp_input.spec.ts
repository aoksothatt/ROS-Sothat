import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import OtpInput from '@/components/OtpInput.vue';

describe('OtpInput.vue Component Tests', () => {
  it('1. Renders 6 numeric input boxes', () => {
    const wrapper = mount(OtpInput, {
      props: { modelValue: '' }
    });

    const inputs = wrapper.findAll('input.otp-box');
    expect(inputs).toHaveLength(6);
  });

  it('2. Populates inputs when modelValue is provided', () => {
    const wrapper = mount(OtpInput, {
      props: { modelValue: '123456' }
    });

    const inputs = wrapper.findAll('input.otp-box');
    expect((inputs[0].element as HTMLInputElement).value).toBe('1');
    expect((inputs[1].element as HTMLInputElement).value).toBe('2');
    expect((inputs[2].element as HTMLInputElement).value).toBe('3');
    expect((inputs[3].element as HTMLInputElement).value).toBe('4');
    expect((inputs[4].element as HTMLInputElement).value).toBe('5');
    expect((inputs[5].element as HTMLInputElement).value).toBe('6');
  });

  it('3. Emits update:modelValue on typing', async () => {
    const wrapper = mount(OtpInput, {
      props: { modelValue: '' }
    });

    const firstInput = wrapper.find('input.otp-box');
    await firstInput.setValue('7');

    expect(wrapper.emitted('update:modelValue')).toBeTruthy();
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['7']);
  });

  it('4. Handles pasting 6 digits and emits complete event', async () => {
    const wrapper = mount(OtpInput, {
      props: { modelValue: '' }
    });

    const container = wrapper.find('.otp-container');
    const mockClipboardEvent = {
      preventDefault: () => {},
      clipboardData: {
        getData: (type: string) => (type === 'text' ? '987654' : '')
      }
    };

    await container.trigger('paste', mockClipboardEvent);

    expect(wrapper.emitted('update:modelValue')).toBeTruthy();
    expect(wrapper.emitted('complete')).toBeTruthy();
    expect(wrapper.emitted('complete')?.[0]).toEqual(['987654']);
  });
});
