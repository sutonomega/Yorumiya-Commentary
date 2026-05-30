# Interrupt Control

割り込み制御は「人の発話」「直前の AI 発話」「event salience」を見る。人が話している時は抑制し、同じ内容は memory で抑制する。

## Transcript Suppression

`CommentPolicy` は VAD に加えて transcript も interrupt signal として扱う。

- `vad_interrupt_salience`: VAD が speech の時でも、この salience 以上の event は発話候補にできる。
- `transcript_interrupt_confidence`: transcript を人の発話 signal とみなす confidence しきい値。
- `transcript_interrupt_salience`: transcript がある時でも、この salience 以上の event は発話候補にできる。

suppression reason は次のように分かれる。

- `vad_speech`: VAD が人の発話を検出した。
- `transcript_speech`: VAD ではなく transcript confidence によって人の発話と判断した。

これにより、VAD が弱い環境でも Whisper adapter の結果から「人が話しているので黙る」を判断できる。
