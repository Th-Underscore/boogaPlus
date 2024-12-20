from typing import Dict, List, Optional, Coroutine
from modules import shared
from modules.chat import delete_history, find_all_histories, get_history_file_path, load_history_after_deletion, redraw_html
from pathlib import Path
import json
import traceback
from html import escape
import copy

import asyncio
import threading

# Colour codes
_ERROR = "\033[1;31m"
_SUCCESS = "\033[1;32m"
_INPUT = "\033[0;33m"
_GRAY = "\033[0;30m"
_HILITE = "\033[0;36m"
_BOLD = "\033[1;37m"
_RESET = "\033[0m"

_current_character = None
_current_id = None
_history_cache = {'visible': [], 'internal': []}
_block_append = False

def validate_cache(i: int):
    """Ensure cache is properly initialized for index i"""
    global _history_cache
    #print(f"Current cache: {_history_cache}")
    
    # Initialize or extend cache if needed
    for cache_type in ['visible', 'internal']:
        if len(_history_cache[cache_type]) <= i:
            print(f"{_GRAY}Extending {cache_type} cache from {len(_history_cache[cache_type])} to {i}{_RESET} {i + 1 - len(_history_cache[cache_type])} {[None] * (i + 1 - len(_history_cache[cache_type]))}")
            _history_cache[cache_type].extend([None] * (i + 1 - len(_history_cache[cache_type])))

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
    
    if state['character_menu'] != _current_character or state['unique_id'] != _current_id:
        print(f"{_HILITE}Cache update needed:{_RESET}")
        print(f"{_BOLD}Character: {_current_character} -> {state['character_menu']}")
        print(f"ID: {_current_id} -> {state['unique_id']}{_RESET}")
        
        # Save current cache if it exists
        if _current_character and _current_id:
            save_cache(_history_cache, get_cache_path(_current_id, _current_character, state['mode']))
        
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
                    print(f"{_SUCCESS}Loaded cache: {_history_cache}{_RESET}")
                else:
                    _history_cache = {'visible': [], 'internal': []}
                    print(f"{_INPUT}Initialized empty cache{_RESET}")
        except Exception as e:
            _history_cache = {'visible': [], 'internal': []}
            print(f"{_ERROR}Initialized empty cache (error: {str(e)}){_RESET}")
        return True
    return False

def append_to_cache(internal_text: str, visible_text: str, state: Dict, is_bot=True, i: Optional[int] = None) -> bool:
    """Append a message to the cache"""
    global _history_cache, _current_character, _current_id, _block_append
    if (_block_append):
        return False
    
    # Update cache if character/chat changed
    update_cache(state)
    
    msg_type = 1 if is_bot else 0  # int(is_bot)
    history = state['history']
    i = len(history['visible']) if i is None else i
    
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
        save_cache(_history_cache, get_cache_path(_current_id, _current_character, state['mode']))
        return True
        
    except Exception as e:
        print(f"{_ERROR}Error appending to cache: {str(e)}{_RESET}")
        traceback.print_exc()
        return False

def save_cache(cache: Dict, path: Path) -> bool:
    """Save the cache to disk"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4)
        return True
    except Exception as e:
        print(f"{_ERROR}Error saving cache:{_RESET} {str(e)}")
        traceback.print_exc()
        return False

def get_position(msg_cache: List) -> Optional[int]:
    """Get the current position of the message's cache"""
    try:
        if len(msg_cache) == 0:
            return None
        return next(i for i, text in enumerate(msg_cache) if not text)  # Find the first None value
    except Exception as e:
        print(f"{_ERROR}Error getting position:{_RESET} {str(e)}")
        traceback.print_exc()
        return None

def get_cache_path(unique_id: str, character: str, mode: str) -> Path:
    """Get the path to the cache file"""
    path = get_history_file_path(unique_id, character, mode).parent
    if not path.is_dir():
        path.mkdir(parents=True)
    return path / f'{unique_id}.json.cache'

# // TGWUI Monkey Patches // #

import modules.chat as chat
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
    global _block_append
    last_msg = state['history']['internal'][-1][1]
    _block_append = True
    history = replace_last_reply(text, state)
    _block_append = False
    if history['internal'][-1][1] != last_msg:
        append_to_cache(history['internal'][-1][1], history['visible'][-1][1], state, is_bot=True, i=len(history['visible']) - 1)
    save_history(history, state['unique_id'], state['character_menu'], state['mode'])
    html = redraw_html(history, state['name1'], state['name2'], state['mode'], state['chat_style'], state['character_menu'])

    return [history, html, ""]
chat.handle_replace_last_reply_click = handle_replace_last_reply_click