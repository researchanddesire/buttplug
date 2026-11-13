/* Resource proof only. No vector table, hardware startup or flashable BIN. */
ENTRY(_start)
MEMORY {
 FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 128K
 RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 20K
}
SECTIONS {
 .text : { *(.text*) *(.rodata*) } > FLASH
 .data : { *(.data*) } > RAM AT> FLASH
 .bss (NOLOAD) : { *(.bss*) *(COMMON) . = ALIGN(8); _end = .; } > RAM
 /DISCARD/ : { *(.comment*) *(.note*) }
}
ASSERT(_end <= ORIGIN(RAM)+LENGTH(RAM)-2048,"candidate consumes reserved 2KiB stack")
