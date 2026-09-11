# Bounded AI specialists

`StructuredSceneInterpreter` extracts quoted scene observations for confirmation. `StructuredPhotoReviewer` assesses image usability. Both validate Pydantic outputs and use the shared provider adapter. Session consent, deterministic safety gates, retry limits, and fallback behavior are enforced by the domain pack and workflow engine. Neither specialist selects graph transitions or authorizes external actions.
