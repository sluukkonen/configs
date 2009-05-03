" Vim script file                                       vim600:fdm=marker:
" FileType:   HTML
" Maintainer: Devin Weaver <vim (at) tritarget.com>
" Location:   http://www.vim.org/scripts/script.php?script_id=301

" This is a wrapper script to add extra html support to xml documents.
" Original script can be seen in xml-plugin documentation.

" Only do this when not done yet for this buffer
" Sun May  3 22:19:33 EEST 2009 Removed the html helpers. -- Saku 
if exists("b:did_ftplugin")
  finish
endif
" Don't set 'b:did_ftplugin = 1' because that is xml.vim's responsability.

let b:html_mode = 1

" On to loading xml.vim
runtime ftplugin/xml.vim
