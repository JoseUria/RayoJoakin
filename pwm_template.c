#include <stdbool.h>
#include <stdint.h>
#include "inc/hw_memmap.h"
#include "driverlib/debug.h"
#include "driverlib/gpio.h"
#include "driverlib/pin_map.h"
#include "driverlib/pwm.h"
#include "driverlib/rom.h"
#include "driverlib/rom_map.h"
#include "driverlib/sysctl.h"
#include "driverlib/uart.h"
#include "utils/uartstdio.h"

uint32_t g_ui32SysClock;

#ifdef DEBUG
void __error__(char *pcFilename, uint32_t ui32Line) { }
#endif

void ConfigureUART(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART0);
    GPIOPinConfigure(GPIO_PA0_U0RX);
    GPIOPinConfigure(GPIO_PA1_U0TX);
    GPIOPinTypeUART(GPIO_PORTA_BASE, GPIO_PIN_0 | GPIO_PIN_1);
    UARTStdioConfig(0, 115200, g_ui32SysClock);
}

void ConfigurePWM(void)
{
    uint32_t ui32PWMClockRate;

    SysCtlPeripheralEnable(SYSCTL_PERIPH_PWM0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOF);

    // PWM2 (PF2)
    GPIOPinConfigure(GPIO_PF2_M0PWM2);
    GPIOPinTypePWM(GPIO_PORTF_BASE, GPIO_PIN_2);

    // PWM3 (PF3)
    GPIOPinConfigure(GPIO_PF3_M0PWM3);
    GPIOPinTypePWM(GPIO_PORTF_BASE, GPIO_PIN_3);

    PWMClockSet(PWM0_BASE, PWM_SYSCLK_DIV_8);

    ui32PWMClockRate = g_ui32SysClock / 8;

    PWMGenConfigure(PWM0_BASE, PWM_GEN_1, PWM_GEN_MODE_UP_DOWN | PWM_GEN_MODE_NO_SYNC);

    PWMGenPeriodSet(PWM0_BASE, PWM_GEN_1, (ui32PWMClockRate / 250));

    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_2, 0);
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_3, 0);

    PWMOutputState(PWM0_BASE, PWM_OUT_2_BIT | PWM_OUT_3_BIT, true);

    PWMGenEnable(PWM0_BASE, PWM_GEN_1);
}

void ConfigureUserLEDs(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOF);

    // Declarar PF4 y PF0 como salidas normales
    GPIOPinTypeGPIOOutput(GPIO_PORTF_BASE, GPIO_PIN_4 | GPIO_PIN_0);
}

void SetPWMDuty(uint32_t pwmOut, uint32_t dutyPercent)
{
    uint32_t period = PWMGenPeriodGet(PWM0_BASE, PWM_GEN_1);
    PWMPulseWidthSet(PWM0_BASE, pwmOut, (period * dutyPercent) / 100);
}

void TurnOnUserLEDs(void)
{
    GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_4 | GPIO_PIN_0, GPIO_PIN_4 | GPIO_PIN_0);
}

void TurnOffUserLEDs(void)
{
    GPIOPinWrite(GPIO_PORTF_BASE, GPIO_PIN_4 | GPIO_PIN_0, 0);
}

int main(void)
{
    g_ui32SysClock = SysCtlClockFreqSet((SYSCTL_XTAL_25MHZ |
                                         SYSCTL_OSC_MAIN |
                                         SYSCTL_USE_PLL |
                                         SYSCTL_CFG_VCO_240), 120000000);

    ConfigureUART();
    ConfigurePWM();
    ConfigureUserLEDs();

    UARTprintf("PWM Control Mode:\n");
    UARTprintf("  '1' -> Ambos PWM al 50%%\n");
    UARTprintf("  '2' -> Ambos apagados y enciende user LEDs\n");
    UARTprintf("  '3' -> PF2 off, PF3 al 60%%\n");
    UARTprintf("  '4' -> PF2 al 20%%, PF3 off\n\n");

    while (1)
    {
        if (UARTCharsAvail(UART0_BASE))
        {
            char input = UARTCharGetNonBlocking(UART0_BASE);

            if (input == '1')
            {
                SetPWMDuty(PWM_OUT_2, 50);
                SetPWMDuty(PWM_OUT_3, 40);
                TurnOffUserLEDs();
                UARTprintf("PWM2 y PWM3 al 50%%\n");
            }
            else if (input == '2')
            {
                SetPWMDuty(PWM_OUT_2, 0);
                SetPWMDuty(PWM_OUT_3, 0);
                TurnOnUserLEDs();
                UARTprintf("PWM2 y PWM3 APAGADOS. User LEDs ENCENDIDOS\n");
            }
            else if (input == '3')
            {
                SetPWMDuty(PWM_OUT_2, 0);
                SetPWMDuty(PWM_OUT_3, 40);
                TurnOffUserLEDs();
                UARTprintf("PWM2 APAGADO, PWM3 al 60%%\n");
            }
            else if (input == '4')
            {
                SetPWMDuty(PWM_OUT_2, 20);
                SetPWMDuty(PWM_OUT_3, 0);
                TurnOffUserLEDs();
                UARTprintf("PWM2 al 20%%, PWM3 APAGADO\n");
            }
        }
    }
}
