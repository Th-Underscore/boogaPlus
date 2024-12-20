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

# input_modifier()
# output_modifier()
# --- See generate_chat_reply_wrapper() monkeypatch

def ui():
    """Create custom gradio elements"""
    from modules.utils import gradio
    
    with gr.Row(visible=True, elem_id="bgpl_row") as bgpl_row:  # CSS already handles visibility
        shared.gradio['bgpl_history_index'] = gr.Number(value=-1, elem_id="bgpl_history_index")   # current message index in history cache
        shared.gradio['bgpl_msg_type'] = gr.Number(value=0, elem_id="bgpl_msg_type")              # 0 for user, 1 for bot
        shared.gradio['bgpl_current_pos'] = gr.Number(value=0, elem_id="bgpl_current_pos")        # current position in message cache
        shared.gradio['bgpl_total_pos'] = gr.Number(value=0, elem_id="bgpl_total_pos")            # total positions available in this message
        shared.gradio['bgpl_navigate'] = gr.Button(elem_id="bgpl_navigate")                       # navigation overlay
        shared.gradio['bgpl_direction'] = gr.Textbox(value="", elem_id="bgpl_direction")          # direction input ('left', 'right')
    
    # Get positions on hover
    for el in ['bgpl_history_index', 'bgpl_msg_type']:
        shared.gradio[el].change(
            fn=get_message_positions,
            inputs=gradio(
                'bgpl_history_index',   # message index input
                'bgpl_msg_type',        # message type input
                'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id',
            ),
            outputs=gradio(
                'bgpl_current_pos',     # current position in text
                'bgpl_total_pos',       # total available positions
            )
        ).then(
            fn=None,
            inputs=None,
            outputs=None,
            js="""() => {
                document.querySelector('#bgpl_current_pos input[type="number"]').dispatchEvent(new Event('change', { 'bubbles': true }));
            }"""
        )
    
    # Navigate through positions
    shared.gradio['bgpl_navigate'].click(
        fn=navigate,
        inputs=gradio(
            'bgpl_direction',       # direction input
            'bgpl_history_index',   # message index input
            'bgpl_msg_type',        # message type input
            'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id'
        ),
        outputs=gradio(
            'display', 'history',   # TGWUI display and history
            'bgpl_current_pos',     # current position in text
            'bgpl_total_pos',       # total available positions
        )
    ).then(
        fn=lambda: None,
        inputs=None,
        outputs=None,
        js="""() => {
            document.querySelector('#bgpl_current_pos input[type="number"]').dispatchEvent(new Event('change', { 'bubbles': true }));
        }"""
    )

def get_message_positions(history_index: float, message_type: float, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character_menu: str, unique_id: str):
    """Get the current and total positions for a message"""
    try:        
        state = {
            'history': history,
            'name1': name1,
            'name2': name2,
            'mode': mode,
            'chat_style': chat_style,
            'character_menu': character_menu,
            'unique_id': unique_id
        }
        
        # Update cache if needed
        cache.update_cache(state)
        
        i = int(history_index)
        msg_type = int(message_type)
        
        if i < 0 or i >= len(history['internal']) or msg_type not in [0, 1]:
            return 0, 0
        
        # Ensure cache is properly initialized with history and retrieve it
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
            print(f"{_ERROR}Error getting position info: {str(e)}{_RESET}")
            traceback.print_exc()
            return 0, 0
    except Exception as e:
        print(f"{_ERROR}Error: {str(e)}{_RESET}")
        traceback.print_exc()
        return 0, 0

def navigate(direction: str, history_index: float, message_type: float, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character_menu: str, unique_id: str):
    try:
        from modules.html_generator import chat_html_wrapper
        
        # Get current position and total positions
        current_pos, total_pos = get_message_positions(history_index, message_type, history, name1, name2, mode, chat_style, character_menu, unique_id)
        if not total_pos:
            return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, 0, 0
        
        # Calculate new position and check if valid
        new_pos = current_pos
        if direction == "right":
            new_pos += 1
            if new_pos >= total_pos:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, min(current_pos, total_pos), total_pos
        elif direction == "left":
            new_pos -= 1
            if new_pos < 0:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, max(current_pos, 0), total_pos
        
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
        
        # Update history
        if new_visible and new_internal:
            history['visible'][i][msg_type] = new_visible
            history['internal'][i][msg_type] = new_internal
        
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, new_pos, total_pos
    except Exception as e:
        print(f"{_ERROR}Error during navigation: {str(e)}{_RESET}")
        traceback.print_exc()
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character_menu), history, 0, 0

def custom_css():
    return open(Path(__file__).parent / 'ui/.css', 'r', encoding='utf-8').read()

def custom_js():
    return open(Path(__file__).parent / 'ui/.js', 'r', encoding='utf-8').read()



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
                cache.append_to_cache(history['internal'][-1][0], history['visible'][-1][0], state, is_bot=False, i=len(history['visible']) - 1)  # history['visible'][-1][0] == escape(text)
            _is_first = False
        yield html, history
        
    cache.append_to_cache(history['internal'][-1][1], history['visible'][-1][1], state, is_bot=True, i=len(history['visible']) - 1)
chat.generate_chat_reply_wrapper = generate_chat_reply_wrapper