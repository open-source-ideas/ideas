// Got the code from here: https://github.com/stiang/remove-markdown/blob/master/index.js

function remove_markdown(string) {
  return string
    // Header
    .replace(/\n={2,}/g, '\n')
    // Strikethrough
    .replace(/~~/g, '')
    // Fenced codeblocks
    .replace(/`{3}.*\n/g, '')
    // Remove HTML tags
    .replace(/<(.*?)>/g, '$1')
    // Remove setext-style headers
    .replace(/^[=\-]{2,}\s*$/g, '')
    // Remove footnotes?
    .replace(/\[\^.+?\](\: .*?$)?/g, '')
    .replace(/\s{0,2}\[.*?\]: .*?$/g, '')
    // Remove images
    .replace(/\!\[.*?\][\[\(].*?[\]\)]/g, '')
    // Remove inline links
    .replace(/\[(.*?)\][\[\(].*?[\]\)]/g, '$1')
    // Remove Blockquotes
    .replace(/>/g, '')
    // Remove reference-style links?
    .replace(/^\s{1,2}\[(.*?)\]: (\S+)( ".*?")?\s*$/g, '')
    // Remove atx-style headers
    .replace(/^\#{1,6}\s*([^#]*)\s*(\#{1,6})?/gm, '$1')
    .replace(/([\*_]{1,3})(\S.*?\S)\1/g, '$2')
    .replace(/(`{3,})(.*?)\1/gm, '$2')
    .replace(/^-{3,}\s*$/g, '')
    .replace(/`(.+?)`/g, '$1')
    .replace(/\n{2,}/g, '\n\n');
}
