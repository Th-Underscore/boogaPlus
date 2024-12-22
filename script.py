from calendar import c
from hmac import new
from typing import Dict, List, Optional, Coroutine
from html import escape, unescape
from pathlib import Path
import traceback
import json
import asyncio
import threading
import logging as logger

import extensions.boogaplus.utils.cache as cache

from modules import shared
from fastapi import FastAPI
import gradio as gr

from modules.extensions import apply_extensions

# Colour codes
_ERROR = "\033[1;31m"
_SUCCESS = "\033[1;32m"
_INPUT = "\033[0;33m"
_GRAY = "\033[0;30m"
_HILITE = "\033[0;36m"
_BOLD = "\033[1;37m"
_RESET = "\033[0m"

params = {
    'display_name': 'boogaPlus',
    'is_tab': True,
}

# input_modifier()
# output_modifier()
# --- See generate_chat_reply_wrapper() monkeypatch

def ui():
    """Create custom gradio elements"""
    from modules.utils import gradio
    
    with gr.Tab(visible=False, elem_id="bgpl_row") as bgpl_row:  # Allow JavaScript retrieval
        shared.gradio['bgpl_navigate'] = gr.Button(value="", elem_id="bgpl_navigate")       # navigate button
        
        # No gr.JSON cuz it's hard to stringify and parse due to its specific structure
        shared.gradio['bgpl_chat_map'] = gr.Textbox(value="[]", elem_id="bgpl_chat_map")    # message indices and types
        shared.gradio['bgpl_chat_data'] = gr.Textbox(value="[]", elem_id="bgpl_chat_data")  # message metadata
        shared.gradio['bgpl_chat_idx'] = gr.Number(value=0, elem_id="bgpl_chat_idx")        # message location in chat UI
        shared.gradio['bgpl_direction'] = gr.Textbox(value="", elem_id="bgpl_direction")    # direction input ('left', 'right')

    # Get positions on hover
    shared.gradio['bgpl_chat_idx'].change(
        fn=retrieve_message_positions,
        inputs=gradio(
            'bgpl_chat_map',        # all message locations
            'bgpl_chat_data',       # original metadata
            'bgpl_chat_idx',        # message location
            'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id',
        ),
        outputs=gradio(
            'bgpl_chat_data',       # updated current position and total available positions
        )
    ).then(
        fn=None,
        inputs=None,
        outputs=None,
        js="""async () => {
            document.querySelector('#bgpl_chat_data textarea').dispatchEvent(new Event('change', { 'bubbles': true }));
        }"""
    )
    
    # Navigate through positions
    shared.gradio['bgpl_navigate'].click(
        fn=navigate,
        inputs=gradio(
            'bgpl_chat_map',        # all message locations
            'bgpl_chat_data',       # original metadata
            'bgpl_chat_idx',        # message location
            'bgpl_direction',       # direction
            'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id',
        ),
        outputs=gradio(
            'display', 'history',   # TGWUI display and history
            'bgpl_chat_data',       # updated metadata
        )
    ).then(
        fn=lambda: None,
        inputs=None,
        outputs=None,
        js="""async () => {
            document.querySelector('#bgpl_chat_data textarea').dispatchEvent(new Event('change', { 'bubbles': true }));
        }"""
    )

def get_message_positions(i: int, msg_type: int, history: Dict):
    try:            
        if i < 0 or i >= len(history['internal']) or msg_type not in [0, 1]:
            return 0, 0
        
        _history_cache = cache._history_cache
        if (i >= len(_history_cache['visible']) or not _history_cache['visible'][i]):
            return 0, 0
        
        try:
            if not _history_cache['visible'][i][msg_type]:
                return 0, 0
            current_pos = _history_cache['visible'][i][msg_type].get('pos', 0)
            total_pos = len(_history_cache['visible'][i][msg_type]['text'])
            return current_pos, total_pos
        except Exception as e:
            print(f"{_ERROR}Error getting position info: {e}{_RESET}")
            traceback.print_exc()
            return 0, 0
    except Exception as e:
        print(f"{_ERROR}Error in get_message_positions: {e}{_RESET}")
        traceback.print_exc()
        return 0, 0

async def retrieve_message_positions(chat_map: str, chat_data: str, chat_index: float, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character_menu: str, unique_id: str):
    """Get the current and total positions for a message"""
    try:
        chat_map = json.loads(chat_map)
        chat_data = json.loads(chat_data)
        state = {
            'history': history,
            'name1': name1,
            'name2': name2,
            'mode': mode,
            'chat_style': chat_style,
            'character_menu': character_menu,
            'unique_id': unique_id
        }
        
        chat_index = int(chat_index)
        if chat_index < 0 or chat_index >= len(chat_map):
            return json.dumps(chat_data)
        
        # Update cache if needed
        cache.update_cache(state)
        
        min_index = len(chat_data)
        max_index = len(chat_map) - 1
        if min_index <= max_index:
            to_extend = max_index + 1 - min_index
            chat_data.extend(get_message_positions(i, msg_type, history) for [i, msg_type] in chat_map[-to_extend:])
        else:
            [i, msg_type] = chat_map[chat_index]
            chat_data[chat_index] = get_message_positions(i, msg_type, history)
        return json.dumps(chat_data)
    except Exception as e:
        print(f"{_ERROR}Error in retrieve_message_positions: {e}{_RESET}")
        traceback.print_exc()
        return json.dumps(chat_data)

async def navigate(chat_map: str, chat_data: str, chat_index: float, direction: str, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character_menu: str, unique_id: str):
    """Navigate left or right through message positions"""
    try:
        from modules.html_generator import chat_html_wrapper
        
        # Retrieve current position and total positions
        chat_data = await retrieve_message_positions(chat_map, chat_data, chat_index, history, name1, name2, mode, chat_style, character_menu, unique_id)  # Also updates cache
        
        chat_map = json.loads(chat_map)
        chat_data = json.loads(chat_data)
        chat_index = int(chat_index)
        
        [history_index, message_type] = chat_map[chat_index]
        [current_pos, total_pos] = chat_data[chat_index]
        if not total_pos:
            return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, json.dumps(chat_data)
        
        # Calculate new position and check if valid
        new_pos = current_pos
        if direction == "right":
            new_pos += 1
            if new_pos >= total_pos:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, json.dumps(chat_data)
        elif direction == "left":
            new_pos -= 1
            if new_pos < 0:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, json.dumps(chat_data)
        
        # Validate and initialize cache
        i = int(history_index)
        msg_type = int(message_type)
        cache.validate_cache(i)
        cache.initialize_cache(i)
        _history_cache = cache._history_cache
        
        # Get messages at new position
        visible_msg_cache = _history_cache['visible'][i][msg_type]
        internal_msg_cache = _history_cache['internal'][i][msg_type]
        visible_msg_cache['pos'] = new_pos
        internal_msg_cache['pos'] = new_pos
        new_visible = visible_msg_cache['text'][new_pos]
        new_internal = internal_msg_cache['text'][new_pos]
        
        chat_data[chat_index] = [new_pos, total_pos]
        
        # Update history
        if new_visible and new_internal:
            history['visible'][i][msg_type] = new_visible
            history['internal'][i][msg_type] = new_internal
        
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, json.dumps(chat_data)
    except Exception as e:
        print(f"{_ERROR}Error during navigation: {e}{_RESET}")
        traceback.print_exc()
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, json.dumps(chat_data) if not type(chat_data) is str else chat_data

def custom_css():
    return open(Path(__file__).parent / 'ui/.css', 'r', encoding='utf-8').read()

def custom_js():
    return open(Path(__file__).parent / 'ui/.js', 'r', encoding='utf-8').read()



import atexit
def cleanup():
    print("(boogaplus) Cleaning up caches...")
    cache.save_cache()
    print("(boogaplus) Finished cleanup.")
atexit.register(cleanup)



# // TGWUI Monkey Patches // #

"""generate_chat_reply_wrapper"""
import modules.chat as chat
character_is_loaded = chat.character_is_loaded
remove_last_message = chat.remove_last_message
send_dummy_message = chat.send_dummy_message
send_dummy_reply = chat.send_dummy_reply
generate_chat_reply = chat.generate_chat_reply
chat_html_wrapper = chat.chat_html_wrapper
save_history = chat.save_history
_generate_chat_reply_wrapper = chat.generate_chat_reply_wrapper
def generate_chat_reply_wrapper(text, state, regenerate=False, _continue=False):
    '''
    Same as above but returns HTML for the UI (BOOGAPLUS MONKEY PATCH)
    '''
    history = state['history']
    _is_first = True
    for html, history in _generate_chat_reply_wrapper(text, state, regenerate, _continue):
        if _is_first:
            if not regenerate and not _continue:
                cache.append_to_cache(history, state, is_bot=False)  # history['visible'][-1][0] == escape(text)
            _is_first = False
        yield html, history
        
    cache.append_to_cache(history, state, is_bot=True)
chat.generate_chat_reply_wrapper = generate_chat_reply_wrapper