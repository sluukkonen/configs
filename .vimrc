syntax on
filetype plugin indent on

set hidden
set number
set ignorecase
set smartcase
set incsearch
set hlsearch
set termguicolors
set tabstop=4
set shiftwidth=4

autocmd BufWritePre * %s/\s\+$//e
