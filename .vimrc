" line numbers
set number
" incremental search
set incsearch
" ignore case in searches, but be case-sensitive if capital letters are used
set ignorecase
set smartcase
" we're using vim, not vi
set nocompatible
" Indentation level
set tabstop=4
set shiftwidth=4
set softtabstop=4
set expandtab
" syntax highlighting
syntax on
" show caret position in the status bar
set ruler
" better buffer handling, ie. don't nag about saving files
set hidden
" backspace deletes eols, tabs, chars
set bs=2
" smarter file prompt
set wildmenu
" no annoying files~
set nobackup
" colorscheme
set t_Co=256 " needed for 256 color colorschemes
colorscheme vylight
" better end and start of line
nmap H ^
nmap L $
omap H ^
omap L $

filetype on
filetype plugin on
filetype indent on

" TextMate-like cmd-enter
imap <D-Enter> <Esc>o

" modifier key
let mapleader = ","
" fuzzyfinder mappings
nmap <leader>f :FuzzyFinderFile<CR>
nmap <leader>d :FuzzyFinderDir<CR>
nmap <leader>b :FuzzyFinderBuffer<CR>
nmap <leader>s :FuzzyFinderTag<CR>

" standard library ctags for C-like languages
set tags=tags,.tags,../tags,~/.stdtags

" fix common typos
command WQ wq
command Wq wq
command W w
command Q q

" Insert mode readline-like bindings
noremap! <C-a>		<Home>
noremap! <C-b>		<Left>
noremap! <C-d>		<Del>
noremap! <C-e>		<End>
noremap! <C-f>		<Right>
noremap! <M-b>  	<S-Left>
noremap! <M-f>	    <S-Right>

" Taglist
nnoremap <silent> <Leader>t :TlistToggle<CR>

" Window management.
nmap <C-J> <C-W>j
nmap <C-K> <C-W>k
nmap <C-H> <C-W>h
nmap <C-L> <C-W>l

" Highligh trailing whitespace.
match Underlined /\s\+$/

" Functions
function! StripTrailingWhitespace()
    %s/\s\+$//e
endfunction

" Update the tags file in the current working directory.
map <Leader>u :ctags -R --c++-kinds=+p --fields=+iaS --extra=+q .<CR>

" Do not use ex-mode.
map Q gq

" Remap insert-mode indentation keys.
" TODO

" Statusline
set statusline=
set statusline+=%3.3n\ " buffer number
set statusline+=%f\ " file name
set statusline+=%h%1*%m%r%w%0* " flags
set statusline+=\[%{strlen(&ft)?&ft:'none'}, " filetype
set statusline+=%{strlen(&fenc)?&fenc:&enc}%{&bomb?'/bom':''}, " encoding
set statusline+=%{&fileformat}] " file format
" set statusline+=%{exists('loaded_VCSCommand')?VCSCommandGetStatusLine():''} " show vcs status
" set statusline+=%{exists('loaded_scmbag')?SCMbag_Info():''} " show vcs status
set statusline+=%= " right align
set statusline+=\[%{exists('loaded_taglist')?Tlist_Get_Tag_Prototype_By_Line(expand('%'),line('.')):'no\ tags'}]\ " show tag prototype
set statusline+=0x%-8B\ " current char
set statusline+=%-14.(%l,%c%V%)\ %<%P " offset
set laststatus=2
