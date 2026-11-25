#pragma once
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
void fake_enter(void);
void fake_exit(void);
#define portENTER_CRITICAL(lock) ((void)(lock),fake_enter())
#define portEXIT_CRITICAL(lock) ((void)(lock),fake_exit())
#define portENTER_CRITICAL_ISR(lock) portENTER_CRITICAL(lock)
#define portEXIT_CRITICAL_ISR(lock) portEXIT_CRITICAL(lock)
