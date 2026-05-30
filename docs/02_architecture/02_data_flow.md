# Data Flow

主要データは `Frame -> SceneState -> CommentaryEvent -> CommentaryContext -> Comment -> SpeechItem` の順に流れる。

音声側は `AudioChunk -> Transcript / VadResult / AudioFeatures` として `CommentaryContext` に合流する。各データには timestamp を持たせ、後続 module が時間軸で比較できるようにする。
