from typing import Dict, List, Optional, Coroutine
from modules import shared
import modules.chat as chat
get_history_file_path = chat.get_history_file_path
from pathlib import Path
import json
import traceback

# Colour codes
_ERROR = "\033[1;31m"
_SUCCESS = "\033[1;32m"
_INPUT = "\033[0;33m"
_GRAY = "\033[0;30m"
_HILITE = "\033[0;36m"
_BOLD = "\033[1;37m"
_RESET = "\033[0m"

_mode = 'html'
_current_character = None
_current_id = None
_history_cache = {'visible': [], 'internal': []}

def validate_list(lst: List, i: int):
    """Ensure list is properly extended to index i"""
    if len(lst) <= i:
        lst.extend([None] * (i + 1 - len(lst)))

def validate_cache(i: int):
    """Ensure cache is properly extended to index i"""
    global _history_cache
    
    # Initialize or extend cache if needed
    for cache_type in ['visible', 'internal']:
        validate_list(_history_cache[cache_type], i)

def initialize_cache(i: int):
    """Initialize message cache dicts at index `i` if nonexistent"""
    global _history_cache
    for cache_type in ['visible', 'internal']:
        if _history_cache[cache_type][i] is None or not isinstance(_history_cache[cache_type][i], list):
            print(f"{_GRAY}Initializing empty {cache_type} cache at index {i}{_RESET}")
            _history_cache[cache_type][i] = [
                {'text': []},  # User message cache
                {'text': []}   # Bot message cache
            ]

def update_cache(state: Dict) -> bool:
    """Update the current cache based on character or chat ID changes"""
    global _current_character, _current_id, _history_cache
    
    if _current_character != state['character_menu'] or _current_id != state['unique_id']:
        print(f"{_HILITE}Cache update needed:{_RESET}")
        print(f"{_BOLD}Character: {_current_character} -> {state['character_menu']}")
        print(f"ID: {_current_id} -> {state['unique_id']}{_RESET}")
        
        # Save current cache if it exists
        if _current_character and _current_id:
            save_cache(state['mode'])
        
        _current_character = state['character_menu']
        _current_id = state['unique_id']
        
        # Load new cache
        path = get_cache_path(_current_id, _current_character, state['mode'])
        if not path.exists():
            _history_cache = {'visible': [], 'internal': []}
            print(f"{_INPUT}Initialized empty cache{_RESET}")
            return True
        try:
            with open(path, 'r', encoding='utf-8') as f:
                contents = f.read()
                if contents:
                    _history_cache = json.loads(contents)
                else:
                    _history_cache = {'visible': [], 'internal': []}
                    print(f"{_INPUT}Initialized empty cache{_RESET}")
        except Exception as e:
            _history_cache = {'visible': [], 'internal': []}
            print(f"{_ERROR}Initialized empty cache (error: {e}){_RESET}")
        return True
    return False

def append_to_cache(history: Dict, state: Dict, is_bot=True) -> bool:
    """Append a message to the end of the cache"""
    global _history_cache, _current_character, _current_id
    
    # Update cache if character/chat changed
    update_cache(state)
    
    msg_type = 1 if is_bot else 0  # int(is_bot)
    i = len(history['visible']) - 1
    visible_text = history['visible'][i][msg_type]
    if not visible_text:
        return False
    internal_text = history['internal'][i][msg_type]
    try:
        # Verify cache structure
        validate_cache(i)
        initialize_cache(i)
        
        # Initialize the message arrays if they don't exist
        if not _history_cache['visible'][i][msg_type] or not _history_cache['internal'][i][msg_type]:
            _history_cache['visible'][i][msg_type] = {'text': []}
            _history_cache['internal'][i][msg_type] = {'text': []}
        
        # Append the strings to the respective lists
        length = len(_history_cache['visible'][i][msg_type]['text'])
        _history_cache['visible'][i][msg_type]['text'].append(visible_text)
        _history_cache['visible'][i][msg_type]['pos'] = length
        _history_cache['internal'][i][msg_type]['text'].append(internal_text)
        _history_cache['internal'][i][msg_type]['pos'] = length
        
        # Save cache to disk
        save_cache(state['mode'])
        return True
        
    except Exception as e:
        print(f"{_ERROR}Error appending to cache: {e}{_RESET}")
        traceback.print_exc()
    return False

def save_cache(mode: Optional[str] = None) -> bool:
    """Save the cache to disk"""
    global _history_cache, _current_character, _current_id
    
    if not _current_id or not _current_character:
        return False
    
    path = get_cache_path(_current_id, _current_character, mode or shared.persistent_interface_state['mode'] or 'chat-instruct')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(_history_cache, f, indent=4)
        return True
    except Exception as e:
        print(f"{_ERROR}Error saving cache:{_RESET} {e}")
        traceback.print_exc()
    return False

def get_position(msg_cache: List) -> Optional[int]:
    """Get the current position of the message's cache"""
    try:
        if len(msg_cache) == 0:
            return None
        return next(i for i, text in enumerate(msg_cache) if not text)  # Find the first None value
    except Exception as e:
        print(f"{_ERROR}Error getting position:{_RESET} {e}")
        traceback.print_exc()
    return None

def get_cache_path(unique_id: str, character: str, mode: str) -> Path:
    """Get the path to the cache file"""
    path = get_history_file_path(unique_id, character, mode).parent
    if not path.is_dir():
        path.mkdir(parents=True)
    return path / f'{unique_id}.json.cache'


# // TGWUI Monkey Patches // #

import logging as logger

"""rename_history"""
get_history_file_path = chat.get_history_file_path
def rename_history(old_id, new_id, character, mode):
    '''
    BOOGAPLUS MONKEY PATCH
    '''
    global _current_id
    if shared.args.multi_user:
        return

    old_p = get_history_file_path(old_id, character, mode)
    new_p = get_history_file_path(new_id, character, mode)
    if new_p.parent != old_p.parent:
        logger.error(f"The following path is not allowed: \"{new_p}\".")
    elif new_p == old_p:
        logger.info("The provided path is identical to the old one.")
    elif new_p.exists():
        logger.error(f"The new path already exists and will not be overwritten: \"{new_p}\".")
    else:
        logger.info(f"Renaming \"{old_p}\" to \"{new_p}\"")
        old_p.rename(new_p)
        logger.info(f"{_BOLD}boogaplus: Renaming \"{old_p}\" ({_current_id}) cache to \"{new_p}\"{_RESET}")
        get_cache_path(old_id, character, mode).rename(get_cache_path(new_id, character, mode))
        _current_id = new_id
chat.rename_history = rename_history

"""handle_delete_chat_confirm_click"""
delete_file = chat.delete_file
_handle_delete_chat_confirm_click = chat.handle_delete_chat_confirm_click
def handle_delete_chat_confirm_click(state):
    '''
    BOOGAPLUS MONKEY PATCH
    '''
    global _current_id
    result = _handle_delete_chat_confirm_click(state)
    delete_file(get_cache_path(state['unique_id'], state['character_menu'], state['mode']))
    _current_id = None
    return result
chat.handle_delete_chat_confirm_click = handle_delete_chat_confirm_click

"""handle_replace_last_reply_click"""
replace_last_reply = chat.replace_last_reply
save_history = chat.save_history
redraw_html = chat.redraw_html
def handle_replace_last_reply_click(text, state):
    '''
    BOOGAPLUS MONKEY PATCH
    '''
    last_msg = state['history']['internal'][-1][1]
    history = replace_last_reply(text, state)
    save_history(history, state['unique_id'], state['character_menu'], state['mode'])
    if history['internal'][-1][1] != last_msg:
        append_to_cache(history, state, is_bot=True)
    html = redraw_html(history, state['name1'], state['name2'], state['mode'], state['chat_style'], state['character_menu'], state['unique_id'])

    return [history, html, ""]
chat.handle_replace_last_reply_click = handle_replace_last_reply_click

"""handle_send_dummy_reply_click"""
send_dummy_reply = chat.send_dummy_reply
def handle_send_dummy_reply_click(text, state):
    '''
    BOOGAPLUS MONKEY PATCH
    '''
    history = send_dummy_reply(text, state)
    save_history(history, state['unique_id'], state['character_menu'], state['mode'])
    append_to_cache(history, state, is_bot=True)
    html = redraw_html(history, state['name1'], state['name2'], state['mode'], state['chat_style'], state['character_menu'], state['unique_id'])
    
    return [history, html, ""]
chat.handle_send_dummy_reply_click = handle_send_dummy_reply_click

"""handle_send_dummy_message_click"""
send_dummy_message = chat.send_dummy_message
def handle_send_dummy_message_click(text, state):
    '''
    BOOGAPLUS MONKEY PATCH
    '''
    history = send_dummy_message(text, state)
    save_history(history, state['unique_id'], state['character_menu'], state['mode'])
    append_to_cache(history, state, is_bot=False)
    append_to_cache(history, state, is_bot=True)
    html = redraw_html(history, state['name1'], state['name2'], state['mode'], state['chat_style'], state['character_menu'], state['unique_id'])
    
    return [history, html, ""]
chat.handle_send_dummy_message_click = handle_send_dummy_message_click