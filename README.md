# boogaPlus

A text-generation-webui extension that adds some nice QoL features to the UI.

## Features

✨ Currently Implemented:
- Message History Navigation
  - Scroll through bot and user messages (cached edits and regenerations)
  - Retrieves both 'internal' and 'visible' texts post-extension modifications for maximum compatibility
  - Smart detection of "Replace last reply" operations
  - Handles chat renaming and deletion
  - Full support for blank messages

<sub>considering switching to full custom JS cache tracking due to Gradio latency (150ms+ !!!)</sub>

## Installation

1. Navigate to your text-generation-webui installation
2. Clone this repository into the `extensions` folder
3. Launch text-generation-webui

## Roadmap

📝 Planned Features:
1. Enhanced Message Selection
   - Click to force-select messages
   - Click-off to force-deselect
2. User Impersonation Navigation
   - Ability to scroll through user impersonations
3. Message Metadata
   - Date/time information for messages
4. Message Management
   - Edit historical messages
   - Revert to previous chat states
   - Insert messages into history
5. Chat History Tools
   - Parse notebook/default into new history
6. Advanced Features
   - Auto-impersonation mode (continuous bot self-conversation)
7. Integrate into TGWUI (full overlay overhaul into direct message HTML)

## Miscellaneous

- TGWUI Unicode quote detection needs fixing (U+201C “ and U+201D ”)
  - Quotes saved literally in JSON, not the Unicode entity
  - Regex matching issues when appending literals or \u201C to quote handling

## Usage

Use the UI. That's it!

- Well, Ctrl+LeftArrow and Ctrl+RightArrow after hovering over a message are fun shortcuts for navigating.

## Known Issues

- Refreshing the page sometimes causes an internal error (refresh again usually does the trick)
- New generations require hovering over the message to update
- Switching tabs doesn't immediately hide the overlay

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. I probably won't be working on this extension in the near future, so please don't hesitate to reach out if you have any questions or suggestions.