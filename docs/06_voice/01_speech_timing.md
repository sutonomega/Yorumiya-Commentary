# Speech Timing

発話タイミングは queue と scheduler で制御する。VAD が人声を検出している場合は基本的に待ち、重要度の高い event のみ短く反応する。
