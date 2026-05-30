# Video Input

動画入力は mp4、OBS、stream capture を将来 adapter として扱う。core は frame の iterable を受け取り、timestamp 付き `Frame` を生成する。
