ORG &1900


.main


.entry 
    lda #22
    jsr &ffee
    lda #128 ; shadow mode 0
    jsr &ffee

    lda #lo(data)
    sta &70
    lda #hi(data)
    sta &71

.line_loop

    jsr getline

    ldx #0
.draw_loop
    lda linedata,x
    jsr &ffee
    inx
    cpx linelength
    beq draw_done
    cpx #79
    bne draw_loop

.draw_done

    lda #13
    jsr &ffee
    lda #10
    jsr &ffee

    jsr &ffe0
    jmp line_loop

    rts


.getchar
    ldy #0
    lda (&70),y

    inc &70
    bne notp
    inc &71
.notp
    rts


.getline
    ldx #0
.char_loop
    jsr getchar
    cmp #13
    beq end_of_line

    sta linedata,x
    inx
    jmp char_loop

.end_of_line
    stx linelength

    sta linedata+0,x
    jsr getchar
    sta linedata+1,x
    rts
     

.data
INCBIN "desire_devil_influences_062020.txt"
EQUB 255



.linedata SKIP 160
.linelength SKIP 1


.end



SAVE "MAIN", main, end, main

PUTFILE "desire_devil_influences_062020.txt", "TEXT", &FFFF, &FFFF
