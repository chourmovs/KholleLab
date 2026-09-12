# Android blackboard input acceptance

MathLive 0.110 uses a contenteditable `keyboard-sink` with `inputmode=none` by
default because its automatic virtual keyboard is the default touch experience.
KHOLLELAB keeps MathLive's supported `manual` virtual-keyboard policy and changes
that **same internal input sink** to `inputmode=text` while the scientific
keyboard is closed. This allows Chrome/TWA to offer the Android IME without a
second editor. MathLive's own input, composition, selection, clipboard, and undo
pipeline remains authoritative.

## Real-device checklist

Run this checklist both in Android Chrome and in the installed KHOLLELAB TWA:

1. Open an editable exercise and tap the middle of the blackboard; confirm the Android keyboard appears.
2. Type `Soit f(x)=x`, including spaces, then try `é è à`, an apostrophe, `1,5`, `1.5`, and `+ - = ( )`.
3. Move the caret by touch and insert text in the middle.
4. Press Android Enter and confirm a new blackboard row appears (with no visible raw LaTeX).
5. Use Backspace across prose, formulae, and the start/end of a row.
6. Long-press, select, copy, and paste text.
7. Open **Clavier scientifique** and insert a fraction, `x²`, and a square root.
8. Close the scientific keyboard, tap the blackboard, and confirm the Android keyboard appears again at the preserved caret.
9. Continue typing, wait for autosave, reload, and confirm the complete solution is restored.
10. Submit the attempt and confirm neither input method opens on the read-only blackboard.

Desktop/mobile emulation can verify focus and event interoperability, but cannot
prove that an actual Android IME or TWA keyboard opened. Record device, Android
version, Chrome version, and pass/fail results when completing this checklist.
