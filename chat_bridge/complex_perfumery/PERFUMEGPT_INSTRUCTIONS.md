# Legacy PerfumeGPT compatibility instructions

`PerfumeGPT` is a legacy label for a spoke chat. The current coordinating chat is
the DeepLuna Chat work hub documented in `DEEPLUNA_CHAT_INSTRUCTIONS.md`.

For compatibility, old commands such as `sync to Complex Perfumery` and
`publish to PerfumeGPT` now use Chat Bridge Protocol v2 and create immutable
packets under `chat_bridge/complex_perfumery/inbox/<conversation-id>/`.

Do not write the legacy root mailbox templates directly. Do not expose secrets or
claim that separate chats share hidden context.
