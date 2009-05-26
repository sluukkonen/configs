" Settings for java files
setlocal omnifunc=javacomplete#Complete 
setlocal completefunc=javacomplete#CompleteParamsInfo 

let b:jcommenter_class_author='Sakumatti Luukkonen <sakumatti.luukkonen@cs.helsinki.fi>'
let b:jcommenter_file_author='Sakumatti Luukkonen <sakumatti.luukkonen@cs.helsinki.fi>'
source ~/.vim/macros/jcommenter.vim
map <Leader>cj :call JCommentWriter()<CR> 
