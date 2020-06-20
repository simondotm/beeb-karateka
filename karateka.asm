


; Karateka Demo


LOAD_ADDR = &3000


; "Release" build config
HIDE_DISPLAY = TRUE        ; set TRUE to hide screen until new image is available (only hides if no shadow ram available)
ENABLE_SWR = TRUE          ; set TRUE to use SWR if available (note all images must be <16Kb in size)
ENABLE_SHADOW = TRUE       ; set TRUE to use Shadow screen if available (makes transitions better)
ENABLE_FADE = TRUE         ; set TRUE to use fade in/out of each image


OSFILE_WORKAROUND = FALSE   ; OSFIND is being awkward on SmartSPI systems

ENABLE_HUFFMAN = FALSE
ENABLE_VGM_FX = FALSE

;-------------------------------------------------------------------
; ZP var allocations
;-------------------------------------------------------------------
ORG &00
GUARD &8F

INCLUDE "lib/exomiser.h.asm"
INCLUDE "lib/vgcplayer.h.asm"

.has_swr        SKIP 1
.has_shadow     SKIP 1
.osfile_params	SKIP 18
.temp_zp        SKIP 2  

;-------------------------------------------------------------------
; EXE chunk
;-------------------------------------------------------------------
ORG &0e00
GUARD LOAD_ADDR




SCRATCH_RAM_ADDR = &3000

; 0E00 - &11FF is a 1Kb buffer 
; used by disksys and filesys as scratch RAM
; also used by 3d model system as scratch RAM
; also used as an offscreen draw buffer

.start



.vgm_buffer_start
; reserve space for the vgm decode buffers (8x256 = 2Kb)
ALIGN 256
.vgm_stream_buffers
    skip 256
    skip 256
    skip 256
    skip 256
    skip 256
    skip 256
    skip 256
    skip 256

.vgm_buffer_end


INCLUDE "lib/bbc.h.asm"
INCLUDE "lib/bbc_utils.h.asm"
INCLUDE "lib/exomiser.asm"
INCLUDE "lib/swr.asm"
INCLUDE "lib/print.asm"     ; feels unnecessary, hardly used, and only for debugging mainly
INCLUDE "lib/disksys.asm"
;INCLUDE "lib/filesys.asm"  ; not needed anymore, as using disksys instead (faster)
INCLUDE "lib/shadowram.asm"
INCLUDE "lib/irq.asm"
; this lot fits in 1Kb with 2 bytes to spare!

INCLUDE "lib/vgcplayer.asm"

\ ******************************************************************
\ *	Bootstrap loader code
\ ******************************************************************


.os_load_system   EQUS "LOAD System", 13
.os_load_main     EQUS "LOAD Main", 13
.os_load_sbank0   EQUS "LOAD SBank0", 13
.os_load_sbank1   EQUS "LOAD SBank1", 13


; disk loader uses hacky filename format (same as catalogue) 
; we use disk loader for SWR banks only
.bank_file1   EQUS "BANK1  $"
.bank_file2   EQUS "BANK2  $"
.bank_file3   EQUS "BANK3  $"
.bank_file4   EQUS "BANK4  $"



.intro_text0 EQUS 12, "K a R a T e K a NOVA 2020", 13, 10, 0
.intro_text1 EQUS "Initializing JIFF system...", 13, 10, 0
.master_text EQUS "This demo is compatible with BBC Master 128 Only. :(", 13, 10, 0


.boot_entry
{
\\ ***** System initialise ***** \\

	\\ *FX 200,3 - clear memory on break as we use OS memory areas and can cause nasty effects
	lda #200
	ldx #3
	jsr osbyte		


    ; check system compatibility
    jsr shadow_check_master
    beq is_master
    MPRINT    master_text
    rts
.is_master



    MPRINT    intro_text0
    MPRINT    intro_text1

    jsr swr_init
    bne swr_ok

    MPRINT swr_fail_text
    rts

.swr_fail_text EQUS "No SWR banks found.", 13, 10, 0
.swr_bank_text EQUS "Found %b", LO(swr_ram_banks_count), HI(swr_ram_banks_count), " SWR banks.", 13, 10, 0
.swr_bank_text2 EQUS " Bank %a", 13, 10, 0
.loading_bank_text EQUS "Loading bank... ", 0
.loading_bank_text2 EQUS "OK", 13, 10, 0
.test_print_number EQUS "%a", 13,10,0


    .swr_ok


	\\ load all SWR banks

    ; PARTY MODE - LOAD CATALOG ONCE ONLY
    jsr disksys_fetch_catalogue


    ; SWR 0
    MPRINT loading_bank_text  
    lda #0
    jsr swr_select_slot
    lda #&80
    ldx #LO(bank_file1)
    ldy #HI(bank_file1)
    jsr disksys_load_file
    MPRINT loading_bank_text2   

    ; SWR 1
    MPRINT loading_bank_text
    lda #1
    jsr swr_select_slot
    lda #&80
    ldx #LO(bank_file2)
    ldy #HI(bank_file2)
    jsr disksys_load_file
    MPRINT loading_bank_text2   

    ; SWR 2
    MPRINT loading_bank_text
    lda #2
    jsr swr_select_slot
    lda #&80
    ldx #LO(bank_file3)
    ldy #HI(bank_file3)
    jsr disksys_load_file
    MPRINT loading_bank_text2

    ; SWR 3
    MPRINT loading_bank_text
    lda #3
    jsr swr_select_slot
    lda #&80
    ldx #LO(bank_file4)
    ldy #HI(bank_file4)
    jsr disksys_load_file
    MPRINT loading_bank_text2


    ; runtime
    rts
}


;-------------------------------------------------------
; Main code entry point
;-------------------------------------------------------
.main
{
    jsr boot_entry



    ; clear display memory before mode switch for clean transition
    jsr clear_vram

    ; clear the shadow RAM too
    jsr shadow_select_ram   
    jsr clear_vram     

    ; setup double buffer
    lda #19:jsr &fff4
    jsr shadow_init_buffers


    ; mode select
    lda #19:jsr &fff4
    lda #22:jsr &ffee
    lda #2:jsr &ffee

    ; turn off cursor
    lda #10:sta &fe00
    lda #32:sta &FE01


    ; start music

    ; initialize the vgm player with a vgc data stream
    lda #hi(vgm_stream_buffers)
    ldx #lo(vgm_data)
    ldy #hi(vgm_data)
    sec ; set carry to enable looping
    jsr vgm_init

    \\ Start our event driven fx
    ldx #LO(event_handler)
    ldy #HI(event_handler)
    JSR start_eventv


    jsr unpack_image
    rts
}




.event_handler
{
	php
	cmp #4
	bne not_vsync

	\\ Preserve registers
	pha:txa:pha:tya:pha

	; prevent re-entry
	lda re_entrant
	bne skip_update
	inc re_entrant

    ; call our music interrupt handler
	;jsr fx_music_irq
    jsr vgm_update

	dec re_entrant
.skip_update

	\\ Restore registers
	pla:tay:pla:tax:pla

	\\ Return
    .not_vsync
	plp
	rts
.re_entrant EQUB 0
}


;-------------------------------------------------------
; Clear all display memory
;-------------------------------------------------------
.clear_vram
{
    lda #&30
    sta clearloop2+2
    ldy #&50
.clearloop
    ldx #0
    txa
.clearloop2
    sta &ff00,x
    inx
    bne clearloop2
    inc clearloop2+2
    dey
    bne clearloop    
    rts
}




;-------------------------------------------------------
; Prepare to unpack an image from the given source address
; X,Y = Lo/Hi address of source image compressed data
;-------------------------------------------------------
.unpack_init
{
	jsr exo_init_decruncher    
    rts
}



;-------------------------------------------------------
; Unpack an image to a destination address
; X,Y = Lo/Hi address of destination address
;-------------------------------------------------------

.framecount EQUW 288
.framecounter EQUW 0

; mode2 format is %babababa where pixels are [ab]
.colourmap EQUB &00, &03, &0C, &0F, &30, &33, &3C, &3F
.unpack_image
{
    lda #0
    sta framecounter + 0
    sta framecounter + 1
    
    lda #0
    jsr swr_select_slot


    lda #0
    sta exo_swr_slot

    ldx #lo(&8000)
    ldy #hi(&8000)

    jsr unpack_init


.frame_loop

    lda #&00
    sta &70
    lda #&30
    sta &71

.pixel_loop

    jsr exo_get_decrunched_byte

    sta &72

    ; run length is top 5 bits
    ; and is *4
    ; 0=4, 1=8, ..., 15=64,31=128 etc.
    and #&F8
    lsr a
    ;lsr a
    ; no need to CLC because C is deffo 0 because of AND above
    adc #4
    sta &73

    ; get pixel colour
    lda &72
    and #&07

    ; if its green, we dont draw anything, we just update draw address
    cmp #&02
    beq check_end

.draw_path

    ; convert colour index to pixel bitmap
    tax
    lda colourmap,x

    ; get run length-1
    ldy &73
    dey

    ; draw run length
.unpack_loop
    sta (&70),y
    dey
    bpl unpack_loop

.check_end

    ; advance draw buffer address by run length
    lda &70
    clc
    adc &73
    sta &70
    lda &71
    adc #0
    sta &71

    ; check for end of frame
    cmp #&30 + &14 + &14 + &14 + &14 ; 80x64 = &1400 bytes
    bne pixel_loop

.frame_done

    ;lda #19:jsr &fff4
    ;lda #19:jsr &fff4
    jsr shadow_swap_buffers

    inc framecounter + 0
    bne notyet
    inc framecounter + 1
.notyet

    lda framecounter + 0
    cmp framecount + 0
    bne frame_loop
    lda framecounter + 1
    cmp framecount + 1
    bne frame_loop

    jmp unpack_image

    rts
}


.vgm_data
INCBIN "music/YM_001.vgc"





.end

PRINT "Gallery program is &", ~(end-start), "bytes (", (end-start)/1024, "Kb), (", (end-start)/256, "sectors) in size"
SAVE "Main", start, end, main


PUTFILE "sequence/bytestream.bin.rle.exo.1", "BANK1", &8000
PUTFILE "sequence/bytestream.bin.rle.exo.2", "BANK2", &8000
PUTFILE "sequence/bytestream.bin.rle.exo.3", "BANK3", &8000

