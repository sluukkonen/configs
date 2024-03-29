syntax on
filetype plugin indent on

set hidden
set number
set ignorecase
set smartcase
set incsearch
set hlsearch
set re=2
set expandtab
set tabstop=4
set softtabstop=4
set shiftwidth=4
set backspace=2

autocmd BufWritePre * %s/\s\+$//e
