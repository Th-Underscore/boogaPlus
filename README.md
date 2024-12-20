# BoogaPlus

A text-generation-webui extension that enhances chat history management and interaction capabilities.

## Features

✨ Currently Implemented:
- Message History Navigation
  - Scroll through bot and user messages (cached)
  - Retrieves both 'internal' and 'visible' texts post-extension modifications for maximum compatibility
  - Smart detection of "Replace last reply" operations
  - Handles chat renaming and deletion
  - Full support for blank messages

## Roadmap

🚀 Planned Features:
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
   - Parse notebook/default format into new history
6. Advanced Features
   - Auto-impersonation mode (continuous bot self-conversation)

## Miscellaneous

- TGWUI Unicode quote detection needs fixing (U+201C “ and U+201D ”)
  - Quotes saved literally in JSON, not the Unicode entity
  - Regex matching issues when appending literals or \u201C to quote handling

## Installation

1. Navigate to your text-generation-webui installation
2. Clone this repository into the `extensions` folder
3. Restart text-generation-webui

## Usage

[Usage instructions to be added]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[License information to be added]

---
Last updated: December 20, 2024