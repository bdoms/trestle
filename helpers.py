import re
from urllib.parse import quote_plus

import htmlmin

CACHE = {}
CACHE_KEYS = []
CACHE_MAX_SIZE = 128 # number of unique entries


def natural_list(string_list):
    # takes a list of strings and renders them like a natural language list
    list_len = len(string_list)
    if list_len == 0:
        return ""
    elif list_len == 1:
        return string_list[0]
    else:
        last_index = len(string_list) - 1
        last_item = string_list[last_index]
        first_items = ', '.join(string_list[:last_index])
        return first_items + " and " + last_item


def url_quote(s):
    return quote_plus(s.encode("utf-8"))


def attr_escape(s):
    return s.replace('"', '&quot;')


def strip_html(string):
    return re.sub(r'<[^<]*?/?>', '', string).strip()


def limit(string, max_len):
    if len(string) > max_len:
        string = string[0:max_len - 3] + "..."
    return string


def plural(string):
    last = string[-1]
    if last == "y":
        string = string[:-1] + "ies"
    elif last != "s":
        string += "s"
    return string


def nl2br(string):
    return string.replace("\n", "<br/>")


ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]


def ordinal(i):
    if i <= len(ORDINALS):
        return ORDINALS[i - 1]
    else:
        s = str(i)
        last_two = s[-2:]
        if last_two in ["11", "12", "13"]:
            return s + "th"
        else:
            last = s[-1]
            if last == "1":
                return s + "st"
            elif last == "2":
                return s + "nd"
            elif last == "3":
                return s + "rd"
            else:
                return s + "th"


def money(i):
    # display an int in cents properly formatted as dollars
    s = str(i)
    while len(s) < 3:
        s = "0" + s
    return "$" + int_comma(s[:-2]) + "." + s[-2:]


def int_comma(i):
    # takes an int and returns it with commas every three digits
    s = str(i)
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))


# decorator to skip straight to the cached version, or cache it if it doesn't exist
def cacheAndRender(skip_check=None, content_type=None):

    def wrap_action(action):
        async def decorate(*args, **kwargs):
            controller = args[0]

            # if we're checking for errors and they're present, then return early to avoid caching
            if skip_check and skip_check(controller):
                return action(*args, **kwargs)

            key = controller.request.path + controller.request.query
            html = CACHE.get(key)

            if html:
                # the action wasn't ever called, so explicitly render the output here
                if content_type:
                    controller.set_header('Content-Type', content_type)
                controller.write(html)
            else:
                await action(*args, **kwargs)
                html = b"".join(controller._write_buffer).decode()

                remove_quotes = content_type != 'application/xml'

                html = htmlmin.minify(html, remove_comments=True, remove_empty_space=True,
                    remove_optional_attribute_quotes=remove_quotes)

                if not controller.debug:
                    cache(key, lambda: html)

        return decorate
    return wrap_action


def cache(key, function):
    # make the key memcache compatible
    key = key.replace(' ', '_')[:250]

    # simple in memory LRU cache, most recently used key is moved to the end, least is at front
    if key in CACHE:
        # move the key to the end since it was just used
        # (this method avoids a temporary state with the key not existing that might not be threadsafe)
        CACHE_KEYS.sort(key=key.__eq__)
        return CACHE[key]

    while len(CACHE_KEYS) >= CACHE_MAX_SIZE:
        remove_key = CACHE_KEYS.pop(0)
        del CACHE[remove_key]

    value = function()
    if key not in CACHE:
        CACHE[key] = value
        CACHE_KEYS.append(key)

    return value


def uncache(key):
    # make the key memcache compatible
    key = key.replace(' ', '_')[:250]

    if key in CACHE:
        del CACHE[key]
        CACHE_KEYS.remove(key)


def clear_cache():
    global CACHE, CACHE_KEYS
    CACHE = {}
    CACHE_KEYS = []
