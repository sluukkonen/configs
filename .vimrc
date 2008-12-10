set number
set incsearch
set ignorecase
set nocompatible
set autoindent
"set smartindent
set cindent
set tabstop=4
set shiftwidth=4
set foldenable
set foldmethod=syntax
colorscheme wombat
syntax on
set ruler
set bs=2

filetype on
filetype plugin on

inoremap {      {}<Left>
inoremap {<CR>  {<CR>}<Esc>O
inoremap {{     {
inoremap {}     {}
"inoremap (     ()<Left>
inoremap )     )<Esc>
               \y2l
			   \:if '))'=="<C-R>=escape(@0,'"\')<CR>"<BAR>
		       \  exec 'normal x'<BAR>
			   \endif<CR>
			   \a""
inoremap /*          /**/<Left><Left>
inoremap /*<Space>   /*<Space><Space>*/<Left><Left><Left>
inoremap /*<CR>      /*<CR>*/<Esc>O
inoremap <Leader>/*  /

" for python indendation
autocmd BufRead *.py set smartindent cinwords=if,elif,else,for,while,try,except,finally,def,class

let mapleader = ","
map <leader>t :FuzzyFinderTextMate<CR>
set guifont=Monaco:h12
 
" snipper snippets
