if !exists('loaded_snippet') || &cp
    finish
endif

function! UpFirst()
    return substitute(@z,'.','\u&','')
endfunction

function! JavaTestFileName(type)
    let filepath = expand('%:p')
    let filepath = substitute(filepath, '/','.','g')
    let filepath = substitute(filepath, '^.\(:\\\)\?','','')
    let filepath = substitute(filepath, '\','.','g')
    let filepath = substitute(filepath, ' ','','g')
    let filepath = substitute(filepath, '.*test.','','')
    if a:type == 1
        let filepath = substitute(filepath, '.[A-Za-z]*.java','','g')
    elseif a:type == 2
        let filepath = substitute(filepath, 'Tests.java','','')
    elseif a:type == 3
        let filepath = substitute(filepath, '.*\.\([A-Za-z]*\).java','\1','g')
    elseif a:type == 4
        let filepath = substitute(filepath, 'Tests.java','','')
        let filepath = substitute(filepath, '.*\.\([A-Za-z]*\).java','\1','g')
    elseif a:type == 5
        let filepath = substitute(filepath, 'Tests.java','','')
        let filepath = substitute(filepath, '.*\.\([A-Za-z]*\).java','\1','g')
        let filepath = substitute(filepath, '.','\l&','')
    endif

    return filepath
endfunction

let st = g:snip_start_tag
let et = g:snip_end_tag
let cd = g:snip_elem_delim

exec "Snippet class class ".st."className".et." {<CR>".st.et."<CR>}"
exec "Snippet for for (".st."int".et." ".st."i".et." = ".st."0".et."; ".st."i".et." < ".st."max".et."; ".st."i".et."++) {<CR>".st.et."<CR>}"
exec "Snippet getset /*<CR>Setter for ".st."fieldName".et.".<CR>@param new".st."fieldName:UpFirst()".et." new value for ".st."fieldName".et."<CR> */<CR>public void set".st."fieldName:UpFirst()".et."(".st."String".et." new".st."fieldName:UpFirst()".et.") {<CR>".st."fieldName".et." = new".st."fieldName:UpFirst()".et.";<CR>}<CR><CR>/*<CR>Getter for ".st."fieldName".et.".<CR>@return ".st."fieldName".et."<CR>*/<CR>public ".st."String".et." get".st."fieldName:UpFirst()".et."() {<CR>return ".st."fieldName".et.";<CR>}<CR><CR>"
exec "Snippet if if (".st.et.") {<CR>".st.et."<CR>}"
exec "Snippet ifel if (".st.et.") {<CR>".st.et."<CR>}<CR>else {<CR>".st.et."<CR>}"
exec "Snippet jtest package ".st."j:JavaTestFileName(1)".et."<CR><CR>import junit.framework.TestCase;<CR>import ".st."j:JavaTestFileName(2)".et.";<CR><CR>/*<CR> * ".st."j:JavaTestFileName(3)".et."<CR> *<CR> * @author ".st.et."<CR> * @since ".st.et."<CR> */<CR>public class ".st."j:JavaTestFileName(3)".et." extends TestCase {<CR><CR>private ".st."j:JavaTestFileName(4)".et." ".st."j:JavaTestFileName(5)".et.";<CR><CR>public ".st."j:JavaTestFileName(4)".et." get".st."j:JavaTestFileName(4)".et."() { return this.".st."j:JavaTestFileName(5)".et."; }<CR>public void set".st."j:JavaTestFileName(4)".et."(".st."j:JavaTestFileName(4)".et." ".st."j:JavaTestFileName(5)".et.") { this.".st."j:JavaTestFileName(5)".et." = ".st."j:JavaTestFileName(5)".et."; }<CR><CR>public void test".st.et."() {<CR>".st.et."<CR>}<CR>}<CR>"
exec "Snippet main public static void main(String[] args) {<CR>".st.et."<CR>}"
exec "Snippet meth ".st."methodName".et."(".st."Parameters".et.") <CR>{<CR>".st.et."<CR>}"
exec "Snippet pr private ".st.et.""
exec "Snippet pu public ".st.et.""
exec "Snippet sout System.out.println(".st.et.");"
exec "Snippet st static ".st.et.""
exec "Snippet try try {<CR>".st.et."<CR>} catch (".st.et." e) {<CR>".st.et."<CR>} finally {<CR>".st.et."<CR>}<CR>"
exec "Snippet vo void ".st.et.""
exec "Snippet while while (".st.et.") {<CR>".st.et."<CR>}"
