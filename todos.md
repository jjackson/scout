# Scout Todo Items

## Plan (in implementation order)

1. [x] Change recipe 'edit' button to 'view' in list
2. [x] Convert recipe steps -> single markdown field
3. [x] Allow editing recipes (edit button on the 'view' page) - done as part of #2, RecipeDetail has editable prompt + Save
4. [x] Remove public sharing of recipes (only have public sharing of results)
5. [x] When running a recipe, redirect to result view (not dialog)
6. [x] Artifacts should be visible in recipe results
7. [x] Clicking a chat in the sidebar should navigate to /chat
8. [x] Tool calls & thinking should be expandable to show details
9. [x] Check that 'thinking' steps are being displayed in the chat - added reasoning block support to stream.py
10. [ ] (human) Review data loading features
11. [ ] CSV import from data_buddy_import.py - needs human input on UX design
    - CLI tool exists at data_buddy_import.py with pandas+sqlalchemy
    - Need to decide: file upload UI? Which DB/schema? Table naming? Column type overrides?
12. [x] Allow sharing of chat history (public / team) including artifacts
    - Added is_shared/is_public/share_token to Thread model with migration
    - Share button in ChatPanel with team + public toggles and copy link
    - Public view at /shared/threads/<token>/ reads from LangGraph checkpointer
    - Public endpoint returns thread metadata, messages (UIMessage format), and artifacts
    - PublicThreadPage renders messages read-only with artifact preview sidebar
13. [ ] (human) Can we make recipe results into a continuable chat session?

## Notes
- Items tagged (human) are skipped until human review
- Item 11 needs human UX design decisions
- Item 13 is tagged (human)
