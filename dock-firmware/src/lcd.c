#include "lcd.h"
#include "board.h"
static uint8_t pixels[1024];
typedef struct { char ch; uint8_t c[5]; } glyph;
static const glyph font[]={
 {'0',{0x3e,0x51,0x49,0x45,0x3e}}, {'1',{0,0x42,0x7f,0x40,0}},
 {'2',{0x42,0x61,0x51,0x49,0x46}}, {'3',{0x21,0x41,0x45,0x4b,0x31}},
 {'4',{0x18,0x14,0x12,0x7f,0x10}}, {'5',{0x27,0x45,0x45,0x45,0x39}},
 {'6',{0x3c,0x4a,0x49,0x49,0x30}}, {'7',{1,0x71,9,5,3}},
 {'8',{0x36,0x49,0x49,0x49,0x36}}, {'9',{6,0x49,0x49,0x29,0x1e}},
 {'A',{0x7e,0x11,0x11,0x11,0x7e}}, {'B',{0x7f,0x49,0x49,0x49,0x36}},
 {'C',{0x3e,0x41,0x41,0x41,0x22}}, {'D',{0x7f,0x41,0x41,0x22,0x1c}},
 {'E',{0x7f,0x49,0x49,0x49,0x41}}, {'F',{0x7f,9,9,9,1}},
 {'G',{0x3e,0x41,0x49,0x49,0x7a}}, {'H',{0x7f,8,8,8,0x7f}},
 {'I',{0,0x41,0x7f,0x41,0}}, {'J',{0x20,0x40,0x41,0x3f,1}},
 {'K',{0x7f,8,0x14,0x22,0x41}}, {'L',{0x7f,0x40,0x40,0x40,0x40}},
 {'M',{0x7f,2,0x0c,2,0x7f}}, {'N',{0x7f,4,8,0x10,0x7f}},
 {'O',{0x3e,0x41,0x41,0x41,0x3e}}, {'P',{0x7f,9,9,9,6}},
 {'Q',{0x3e,0x41,0x51,0x21,0x5e}}, {'R',{0x7f,9,0x19,0x29,0x46}},
 {'S',{0x46,0x49,0x49,0x49,0x31}}, {'T',{1,1,0x7f,1,1}},
 {'U',{0x3f,0x40,0x40,0x40,0x3f}}, {'V',{0x1f,0x20,0x40,0x20,0x1f}},
 {'W',{0x3f,0x40,0x38,0x40,0x3f}}, {'X',{0x63,0x14,8,0x14,0x63}},
 {'Y',{7,8,0x70,8,7}}, {'Z',{0x61,0x51,0x49,0x45,0x43}},
 {':',{0,0x36,0x36,0,0}}, {'/',{0x20,0x10,8,4,2}},
 {'.',{0,0x60,0x60,0,0}}, {'-',{8,8,8,8,8}},
 {'+',{8,8,0x3e,8,8}}, {'=',{0x14,0x14,0x14,0x14,0x14}}
};
static void command(uint8_t byte){board_lcd_write(false,byte);}
static void clear(void){for(unsigned j=0;j<1024;++j)pixels[j]=0;}
static void text(unsigned row,unsigned column,const char *s){
    unsigned x=column*6;
    while(*s && x+5<128 && row<8){
        for(unsigned k=0;k<sizeof(font)/sizeof(font[0]);++k)if(font[k].ch==*s)
            for(unsigned c=0;c<5;++c)pixels[row*128+x+c]=font[k].c[c];
        ++s;x+=6;
    }
}
static void number(unsigned row,unsigned col,unsigned value){
    char buf[6];unsigned p=5;buf[p]=0;
    do{buf[--p]=(char)('0'+value%10);value/=10;}while(value && p);
    text(row,col,buf+p);
}
static void temperature(unsigned row,unsigned col,int16_t centi){
    if(centi<0){text(row,col,"-");centi=(int16_t)-centi;++col;}
    number(row,col,(unsigned)centi/100);text(row,col+2,".");number(row,col+3,((unsigned)centi/10)%10);
}
void lcd_contrast(uint8_t contrast){command(0x81);command(contrast&63u);}
void lcd_flush_page(unsigned page){
    if(page>=8)return;
    command((uint8_t)(0xb0u|page));command(0x10);command(0x00);
    for(unsigned x=0;x<128;++x)board_lcd_write(true,pixels[page*128+x]);
}
void lcd_flush(void){
    for(unsigned page=0;page<8;++page)lcd_flush_page(page);
}
void lcd_init(uint8_t contrast){
    board_lcd_reset(false);board_delay_ms(5);board_lcd_reset(true);board_delay_ms(20);
    /* Newhaven selected-module init: 1/9bias, normalADC, reverseCOM,
       normalpoints, startline0, resistorratio5, electronicvolume, allpumpstages. */
    const uint8_t setup[]={0xae,0xa2,0xa0,0xc8,0xa4,0x40,0x25};
    for(unsigned j=0;j<sizeof(setup);++j)command(setup[j]);
    lcd_contrast(contrast);command(0x2f);board_delay_ms(20);
    clear();lcd_flush();command(0xaf);
}
void lcd_render(const dock_app *a,const dock_inputs *i){
    clear();text(0,0,"COMPASS DOCK EVT");text(1,0,dock_state_text(a->state));
    if(a->fault!=FAULT_NONE)text(2,0,dock_fault_text(a->fault));
    else {
        switch(i->source){
        case SOURCE_UNATTACHED:text(2,0,"SOURCE: UNATTACHED");break;
        case SOURCE_DEFAULT:text(2,0,"SOURCE: USB DEFAULT");break;
        case SOURCE_1A5:text(2,0,"SOURCE: TYPE-C 1.5A");break;
        case SOURCE_3A:text(2,0,"SOURCE: TYPE-C 3A");break;
        }
    }
    text(3,0,"BASE");text(3,11,"LID");
    if(i->ntc_valid){temperature(3,5,i->base_centi_c);temperature(3,15,i->lid_centi_c);text(3,19,"C");}
    else{text(3,5,"--.-");text(3,15,"--.-");}
    text(4,0,"TRIAL");number(4,6,a->trial_seconds);
    if(a->state==DOCK_RUNNING){text(4,9,"S LEFT");number(4,16,a->remaining_seconds);text(4,20,"S");}
    else text(4,10,"SECONDS");
    if(a->contrast_mode){text(5,0,"L/R: CONTRAST");number(5,15,a->contrast);}
    else text(5,0,"L/R: TRIAL SECONDS");
    text(6,0,a->state==DOCK_RUNNING?"CENTER: STOP":"HOLD L+R: CONTRAST");
    text(7,0,"UNQUALIFIED UV TRIAL");
}
#ifdef DOCK_WIRED_MAIN
static void clear_row(unsigned row)
{
    for (unsigned x = 0; x < 128; ++x) pixels[row * 128 + x] = 0;
}

void lcd_render_host(const host_client *host, bool qualified, bool mode_access)
{
    if (!mode_access && !host->local_requested) return;
    if (mode_access) {
        clear_row(1);
        text(1, 0, "UV INTERLOCK OPEN");
    }
    clear_row(5);
    if (!qualified) {
        text(5, 0, "USB: PC");
    } else if (host->mode_pending ||
               (host->have_status && ((host->flags & HOST_STATUS_TRANSITION) ||
                (!host->local_requested && (host->flags & HOST_STATUS_LOCAL))))) {
        text(5, 0, "USB: SWITCHING");
    } else if (!host->local_requested) {
        text(5, 0, "HOLD R: LOCAL USB");
    } else if (host->have_status && (host->flags & HOST_STATUS_TIP_VALID)) {
        int32_t centi = host->tip_centi_c;
        unsigned col = 4;
        text(5, 0, "TIP");
        if (centi < 0) {
            text(5, col++, "-");
            centi = -centi;
        }
        unsigned whole = (unsigned)centi / 100u;
        number(5, col, whole);
        col += whole >= 100 ? 3 : (whole >= 10 ? 2 : 1);
        text(5, col, ".");
        number(5, col + 1, ((unsigned)centi / 10u) % 10u);
        text(5, col + 3, "C");
    } else if (host->have_status && (host->flags & HOST_STATUS_FAULT)) {
        text(5, 0, "USB HOST FAULT");
    } else if (!host->have_status || !(host->flags & HOST_STATUS_LOCAL)) {
        text(5, 0, "LOCAL USB WAIT");
    } else if (!(host->flags & HOST_STATUS_ATTACHED)) {
        text(5, 0, "WAIT FOR USB DEVICE");
    } else {
        text(5, 0, "TIP: NO FRESH DATA");
    }
    if (qualified && mode_access && host->local_requested) {
        clear_row(6);
        text(6, 0, "HOLD R: PC USB");
    }
}
#endif
