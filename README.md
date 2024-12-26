# boogaPlus

A text-generation-webui extension that adds some nice QoL features to the UI.

## ✨ Features

- Message History Navigation
  - Scroll through bot and user messages (cached edits and regenerations)
    - Click to force-select messages
    - Re-click or click-off to force-deselect
  - Retrieves both 'internal' and 'visible' texts post-extension modifications for maximum compatibility
  - Smart detection of "Replace last reply" operations
  - Handles chat renaming and deletion
  - Full support for blank messages

## 🔧 Installation

1. Navigate to your text-generation-webui installation
2. Clone this repository into the `extensions` folder with the lowercase name `boogaplus`:
   - `git clone https://github.com/Th-Underscore/boogaPlus extensions/boogaplus`
3. Launch text-generation-webui

## 📝 Roadmap

1. Reimplement nav overlay mode (for now, just revert to a previous commit if you prefer the overlay)
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
7. Integrate into TGWUI

## 📖 Usage

- On/off to display the nav container
- Click either nav button to navigate
- Click on a message to select it:
   - Ctrl+LeftArrow and Ctrl+RightArrow to navigate through edits / generations
   - Ctrl+UpArrow and Ctrl+DownArrow to scroll through messages

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. CSS styling upgrades are especially welcome.

I probably won't be working on this extension in the near future, so please don't hesitate to reach out if you have any questions or suggestions.