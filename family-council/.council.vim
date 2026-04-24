" Family Council — purple
syntax on
set background=dark
set wrap linebreak nolist number showmode showcmd laststatus=2 ruler autoread
set scrolloff=4 sidescrolloff=8
hi Normal       ctermfg=252 ctermbg=234 guifg=#e8e8e8 guibg=#1a1a1a
hi LineNr       ctermfg=141 guifg=#b48cff
hi CursorLine   ctermbg=236 cterm=NONE
hi CursorLineNr ctermfg=213 guifg=#ff9dff cterm=bold
hi StatusLine   ctermfg=234 ctermbg=141 guifg=#1a1a1a guibg=#b48cff cterm=bold
hi StatusLineNC ctermfg=244 ctermbg=237
hi Title        ctermfg=141 guifg=#b48cff cterm=bold
hi Visual       ctermbg=55
hi Search       ctermfg=234 ctermbg=213
autocmd FileType markdown setlocal wrap linebreak conceallevel=0
autocmd FileType markdown hi markdownH1 ctermfg=141 cterm=bold
autocmd FileType markdown hi markdownH2 ctermfg=213 cterm=bold
autocmd FileType markdown hi markdownBold ctermfg=213 cterm=bold
autocmd FileType markdown hi markdownItalic ctermfg=183 cterm=italic
autocmd FileType markdown hi markdownBlockquote ctermfg=141
autocmd CursorHold * silent! write
set updatetime=20000
set cursorline
