" Vim script file                                       vim600:fdm=marker:
" FileType:   HTML
" Maintainer: Devin Weaver <vim (at) tritarget.com>
" Location:   http://www.vim.org/scripts/script.php?script_id=301

" This is a wrapper script to add extra html support to xml documents.
" Original script can be seen in xml-plugin documentation.

" Only do this when not done yet for this buffer
" Sun May  3 22:19:33 EEST 2009 Removed the html helpers. -- Saku 
" Mon May  4 10:39:08 EEST 2009 Added html filetype tweaks. -- Saku

if exists("b:did_ftplugin")
  finish
endif
" Don't set 'b:did_ftplugin = 1' because that is xml.vim's responsability.

let b:html_mode = 1

" html-filetype tweaks
let g:html_indent_inctags = "html,body,head,tbody,p,li"
setlocal shiftwidth=2 | setlocal tabstop=2 | setlocal expandtab

" On to loading xml.vim
runtime ftplugin/xml.vim
