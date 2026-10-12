# Welcome to Star City

**Category:** Web · **Points:** 15 · **Solves:** 591 · **Challenge ID:** 38

> Welcome to Star City. Home of stars galore. But is there more to be seen than meets the eye?

## Challenge

Welcome to Star City. Home of stars galore. But is there more to be seen than
meets the eye?

```
http://REMOTE_HOST/
```

Flag format: `CSSCTF{...}`

No downloadable attachment — just a live site served by nginx.

## Initial analysis

A single `GET /` returns a tiny 309-byte HTML page:

```html
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>STAR1001</title><link rel="stylesheet" href="style.css"></head><body><div class="skyline" aria-hidden="true"></div><main><h1 data-text="Welcome to Star City">Welcome to Star City</h1></main></body></html>
```

The body holds nothing but a heading. The only resource it references is the
same-origin stylesheet `style.css`, which comes back as `HTTP/1.1 200 OK` with
13,619 bytes of CSS. "More to be seen than meets the eye" points straight at the
one asset the page actually loads — so the next step is to read the CSS itself,
not just let the browser apply it.

Both the recovered HTML (`restored.body`) and the stylesheet (`style.css`) are
committed here.

## Vulnerability / core concept

This is a "read the source" web warmup: the flag is hidden in a CSS comment at
the very end of `style.css`, encoded so it doesn't jump out. The payload is
Base64 **without padding**, and once decoded it is a **percent-encoded** string —
two light layers of obfuscation stacked on top of each other.

## Exploitation

1. Fetch the page and follow its one reference to the stylesheet:

   ```bash
   curl -s http://REMOTE_HOST/ -o restored.body
   curl -s http://REMOTE_HOST/style.css -o style.css
   ```

2. The last line of `style.css` is a trailing comment holding a Base64 blob:

   ```css
   } /*Q1NTQ1RGJTdCd2VfQlUxTFRfdGhpc19jaXR5X2Zyb21fcjBja19hbmRfUjAxMSU3RA*/
   ```

3. The blob has no `=` padding, so pad it to a multiple of four, Base64-decode,
   then percent-decode the result:

   ```bash
   python3 -c "
   import base64, urllib.parse
   b = 'Q1NTQ1RGJTdCd2VfQlUxTFRfdGhpc19jaXR5X2Zyb21fcjBja19hbmRfUjAxMSU3RA'
   b += '=' * (-len(b) % 4)
   dec = base64.b64decode(b).decode()
   print(dec)                          # CSSCTF%7Bwe_BU1LT_this_city_from_r0ck_and_R011%7D
   print(urllib.parse.unquote(dec))    # CSSCTF{we_BU1LT_this_city_from_r0ck_and_R011}
   "
   ```

   The Base64 decodes to `CSSCTF%7B...%7D`; percent-decoding `%7B`/`%7D` back to
   `{`/`}` yields the flag.

## Flag

```
CSSCTF{we_BU1LT_this_city_from_r0ck_and_R011}
```

## Key takeaways

- When a page's body is empty, read every resource it pulls in — the flag often
  hides in a stylesheet, script, or comment the browser never shows you.
- Base64 can appear without `=` padding; re-pad to a multiple of four before decoding.
- Don't stop at the first decode — a Base64 result that still looks escaped
  (`%7B`, `%7D`) needs a second pass (percent-decoding) to reveal the real flag.
