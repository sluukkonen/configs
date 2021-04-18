syntax on
filetype plugin indent on

set hidden
set number
set ignorecase
set smartcase
set incsearch
set hlsearch

autocmd BufWritePre * %s/\s\+$//e
