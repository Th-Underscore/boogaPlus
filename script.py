from calendar import c
from hmac import new
from typing import Dict, List, Optional, Coroutine, Iterable
from html import escape, unescape
from pathlib import Path
import traceback
import json
import asyncio
import threading
import logging as logger
from functools import reduce
from operator import getitem

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
    'display_name': 'boogaPlus'
}

def recursive_get(data: Dict | Iterable, keyList: List[int | str], default=None):
    """Iterate nested dictionary / iterable."""
    try:
        return reduce(getitem, keyList, data)
    except KeyError:
        return default
    except IndexError:
        return default
    except TypeError:
        return default
    except Exception as e:
        print(f"{_ERROR}Error getting value:{_RESET} {e}")
        traceback.print_exc()
        return None
def length(data: Iterable):
    """Get length of iterable with try catch."""
    try:
        return len(data)
    except TypeError:
        return 0
    except Exception as e:
        print(f"{_ERROR}Error getting length:{_RESET} {e}")
        traceback.print_exc()
        return 0

# input_modifier()
# output_modifier()
# --- See generate_chat_reply_wrapper() monkeypatch

def ui():
    """Create custom gradio elements"""
    from modules.utils import gradio
    
    with gr.Tab(visible=True, label="boogaPlus", elem_id="bgpl_tab") as bgpl_row:
        with gr.Row(visible=False, elem_id="bgpl_info_row"):
            shared.gradio['bgpl_startup'] = gr.Button(elem_id="bgpl_startup")                       # chat startup handler
            shared.gradio['bgpl_navigate'] = gr.Button(value="", elem_id="bgpl_navigate")           # navigate() handler
            
            shared.gradio['bgpl_history_index'] = gr.Number(value=0, elem_id="bgpl_history_index")  # selected message location in history
            shared.gradio['bgpl_message_type'] = gr.Number(value=0, elem_id="bgpl_message_type")    # selected message type (0 = user, 1 = bot)
            shared.gradio['bgpl_direction'] = gr.Textbox(value="", elem_id="bgpl_direction")        # selected direction input ('left', 'right')
            
        with gr.Row(visible=True, elem_id="bgpl_display_row"):
            shared.gradio['bgpl_display_mode'] = gr.Radio(choices=['html', 'overlay (disabled)', 'off'], value='html', label="", elem_classes=['slim-dropdown'], interactive=True, elem_id="bgpl_display_mode")
    
    # Startup event
    shared.gradio['bgpl_startup'].click(
        fn=startup,
        inputs=gradio('history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id'),
        outputs=gradio('display'),  # TGWUI display
        show_progress=False
    ).then(
        fn=None,
        inputs=None,
        outputs=None,
        js="""async () => {
            document.querySelector('#bgpl_navigate').dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        show_progress=False
    )
    
    shared.gradio['bgpl_display_mode'].change(
        fn=change_display_mode,
        inputs=gradio(
            'bgpl_display_mode',
            'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id',
        ),
        outputs=gradio('display'),
        show_progress=False
    )
    
    # Navigate through positions
    shared.gradio['bgpl_navigate'].click(
        fn=navigate,
        inputs=gradio(
            'bgpl_history_index',
            'bgpl_message_type',
            'bgpl_direction',
            'history', 'name1', 'name2', 'mode', 'chat_style', 'character_menu', 'unique_id',
        ),
        outputs=gradio(
            'display', 'history',  # TGWUI display and history
        ),
        show_progress='full'
    ).then(
        fn=None,
        inputs=None,
        outputs=None,
        js="""async () => {
            document.querySelector('#bgpl_navigate').dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        show_progress='full'
    )

def startup(history: Dict, name1: str, name2: str, mode: str, chat_style: str, character: str, unique_id: str):
    """Chat history draw handler for boogaPlus startup."""
    return chat.redraw_html(history, name1, name2, mode, chat_style, character, unique_id, reset_cache=True)

def change_display_mode(display_mode: str, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character: str, unique_id: str):
    """Change boogaPlus display mode in chat UI."""
    if display_mode == 'off':
        cache._mode = 'off'
        return chat.redraw_html(history, name1, name2, mode, chat_style, character, unique_id, reset_cache=True)
    
    if display_mode == 'overlay (disabled)':
        cache._mode = 'overlay'
        return chat.redraw_html(history, name1, name2, mode, chat_style, character, unique_id, reset_cache=True)
    
    if display_mode == 'html':
        cache._mode = 'html'
        return chat.redraw_html(history, name1, name2, mode, chat_style, character, unique_id, reset_cache=True)
    
    return chat.redraw_html(history, name1, name2, mode, chat_style, character, unique_id, reset_cache=True)

def get_message_positions(i: int, msg_type: int):
    """Recursively get cached message position and total message positions."""
    msg_data = recursive_get(cache._history_cache, ['visible', i, msg_type])
    return recursive_get(msg_data, ['pos'], 0), length(recursive_get(msg_data, ['text'], []))

def navigate(i: float, msg_type: float, direction: str, history: Dict, name1: str, name2: str, mode: str, chat_style: str, character: str, unique_id: str):
    """Navigate left or right through message positions."""
    try:
        from modules.html_generator import chat_html_wrapper
        
        state = {
            'history': history,
            'name1': name1,
            'name2': name2,
            'mode': mode,
            'chat_style': chat_style,
            'character_menu': character,
            'unique_id': unique_id
        }
        
        i = int(i)
        msg_type = int(msg_type)
        
        # Retrieve current position and total positions
        cache.update_cache(state)
        current_pos, total_pos = get_message_positions(i, msg_type)
        
        if not total_pos:
            return chat_html_wrapper(history, name1, name2, mode, chat_style, character, unique_id), history
        
        # Calculate new position and check if valid
        new_pos = current_pos
        if direction == "right":
            new_pos += 1
            if new_pos >= total_pos:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character, unique_id), history
        elif direction == "left":
            new_pos -= 1
            if new_pos < 0:
                return chat_html_wrapper(history, name1, name2, mode, chat_style, character, unique_id), history
        
        # Validate and initialize cache
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
        
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character, unique_id), history
    except Exception as e:
        print(f"{_ERROR}Error during navigation: {e}{_RESET}")
        traceback.print_exc()
        return chat_html_wrapper(history, name1, name2, mode, chat_style, character, unique_id), history

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
    yield chat_html_wrapper(history, state['name1'], state['name2'], state['mode'], state['chat_style'], state['character_menu'], state['unique_id']), history
        
chat.generate_chat_reply_wrapper = generate_chat_reply_wrapper




"""html"""
import time
import modules.html_generator as html_generator
chat_styles = html_generator.chat_styles
convert_to_markdown_wrapped = html_generator.convert_to_markdown_wrapped
def generate_cai_chat_html(history, name1, name2, style, character, unique_id, reset_cache=False):
    output = f'<style>{chat_styles[style]}</style><div class="chat cai-chat" id="chat"><div class="messages">'

    # We use ?character and ?time.time() to force the browser to reset caches
    img_bot = f'<img src="file/cache/pfp_character_thumb.png?{character}" class="pfp_character">' if Path("cache/pfp_character_thumb.png").exists() else ''
    img_me = f'<img src="file/cache/pfp_me.png?{time.time() if reset_cache else ""}">' if Path("cache/pfp_me.png").exists() else ''
    
    try: cache.update_cache({
        'history': history,
        'name1': name1,
        'name2': name2,
        'mode': 'chat-instruct',
        'chat_style': style,
        'character_menu': character,
        'unique_id': unique_id
    })
    except: pass

    for i, _row in enumerate(history):
        row = [convert_to_markdown_wrapped(entry, use_cache=i != len(history) - 1) for entry in _row]

        if row[0]:  # don't display empty user messages
            try: current_pos, total_pos = get_message_positions(i, 0)
            except: current_pos, total_pos = 0, 0
            output += f"""
                  <div class="message" data-history-index="{i}" data-message-type="0">
                    <div class="circle-you">
                      {img_me}
                    </div>
                    <div class="text">
                      <div class="username">
                        {name1}
                      </div>
                      <div class="message-body">
                        {row[0]}
                      </div>
                    </div>
                    <div class="boogaplus-container"{' hidden="true"' if cache._mode == 'off' else ''}>
                      <div class="nav-container"{' hidden="true"' if total_pos <= 1 else ''}>
                        <button class="nav-arrow nav-left"{' activated="true"' if current_pos != 0 else ''}><</button>
                        <div class="nav-pos">{current_pos+1}/{total_pos}</div>
                        <button class="nav-arrow nav-right"{' activated="true"' if current_pos <= total_pos - 2 else ''}>></button>
                      </div>
                    </div>
                  </div>
                """

        try: current_pos, total_pos = get_message_positions(i, 1)
        except: current_pos, total_pos = 0, 0
        output += f"""
              <div class="message" data-history-index="{i}" data-message-type="1">
                <div class="circle-bot">
                  {img_bot}
                </div>
                <div class="text">
                  <div class="username">
                    {name2}
                  </div>
                  <div class="message-body">
                    {row[1]}
                  </div>
                </div>
                <div class="boogaplus-container"{' hidden="true"' if cache._mode == 'off' else ''}>
                  <div class="nav-container"{' hidden="true"' if total_pos <= 1 else ''}>
                    <button class="nav-arrow nav-left"{' activated="true"' if current_pos != 0 else ''}><</button>
                    <div class="nav-pos">{current_pos+1}/{total_pos}</div>
                    <button class="nav-arrow nav-right"{' activated="true"' if current_pos <= total_pos - 2 else ''}>></button>
                  </div>
                </div>
              </div>
            """

    output += "</div></div>"
    
    return output
html_generator.generate_cai_chat_html = generate_cai_chat_html

def generate_chat_html(history, name1, name2, reset_cache=False):
    output = f'<style>{chat_styles["wpp"]}</style><div class="chat wpp" id="chat"><div class="messages">'

    for i, _row in enumerate(history):
        row = [convert_to_markdown_wrapped(entry, use_cache=i != len(history) - 1) for entry in _row]

        if row[0]:  # don't display empty user messages
            try: current_pos, total_pos = get_message_positions(i, 0)
            except: current_pos, total_pos = 0, 0
            output += f"""
              <div class="message" data-history-index="{i}" data-message-type="0">
                <div class="text-you">
                  <div class="message-body">
                    {row[0]}
                  </div>
                  <div class="boogaplus-container">
                    <div class="nav-container"{' hidden="true"' if total_pos <= 1 else ''}>
                      <button class="nav-arrow nav-left"{' activated="true"' if current_pos != 0 else ''}><</button>
                      <div class="nav-pos">{current_pos+1}/{total_pos}</div>
                      <button class="nav-arrow nav-right"{' activated="true"' if current_pos <= total_pos - 2 else ''}>></button>
                    </div>
                  </div>
                </div>
              </div>
            """

        try: current_pos, total_pos = get_message_positions(i, 1)
        except: current_pos, total_pos = 0, 0
        output += f"""
          <div class="message" data-history-index="{i}" data-message-type="1">
            <div class="text-bot">
              <div class="message-body">
                {row[1]}
              </div>
              <div class="boogaplus-container">
                <div class="nav-container"{' hidden="true"' if total_pos <= 1 else ''}>
                  <button class="nav-arrow nav-left"{' activated="true"' if current_pos != 0 else ''}><</button>
                  <div class="nav-pos">{current_pos+1}/{total_pos}</div>
                  <button class="nav-arrow nav-right"{' activated="true"' if current_pos <= total_pos - 2 else ''}>></button>
                </div>
              </div>
            </div>
          </div>
        """

    output += "</div></div>"
    return output
html_generator.generate_chat_html = generate_chat_html