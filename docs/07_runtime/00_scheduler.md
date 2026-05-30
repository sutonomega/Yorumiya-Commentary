# Scheduler

scheduler は tick、frame、inference、speech の周期を管理する。`RealtimeScheduler.due()` が指定 interval を満たした処理だけを実行する。
