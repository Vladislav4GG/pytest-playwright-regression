# pages/klarna_popup_page.py
import random
import re
import time
from playwright.sync_api import Page, expect, TimeoutError as PWTimeoutError


class KlarnaPopupPage:
    def __init__(self, page: Page):
        self.page = page

    # ---------------- helpers ----------------

    def _rand_email(self, base: str = "vlad.ponomarenko") -> str:
        return f"{base}+{random.randint(10000, 99999)}@keenethics.com"

    def _click_continue(self, timeout: int):
        btn = self.page.get_by_role("button", name=re.compile(r"^\s*continue\s*$", re.I)).first
        expect(btn).to_be_visible(timeout=timeout)
        expect(btn).to_be_enabled(timeout=timeout)
        btn.click()

    def _normalize_gb_mobile(self, phone: str) -> str:
        """
        Повертає GB mobile у форматі E.164: +44XXXXXXXXXX
        Приймає:
        - 07400123456
        - +447400123456
        - 447400123456
        """
        p = re.sub(r"[^\d+]", "", phone).strip()

        # already +44...
        if p.startswith("+44"):
            digits = re.sub(r"\D", "", p)  # 44...
            return f"+{digits}"

        # 44...
        if p.startswith("44"):
            digits = re.sub(r"\D", "", p)
            return f"+{digits}"

        # 0XXXXXXXXXX -> +44XXXXXXXXXX (типово UK mobile 11 цифр і починається з 07)
        if re.fullmatch(r"0\d{10}", p):
            return "+44" + p[1:]

        # якщо сюди дійшли — це сміття/не GB
        raise ValueError(
            f"Klarna GB: phone must be UK mobile. Got '{phone}'. "
            f"Use +447400123456 or 07400123456."
        )

    # ---------------- steps ----------------

    def _step_phone(self, phone: str, timeout: int):
        """
        Phone screen on login.playground.klarna.com.
        Важливо:
        - вводимо UK mobile
        - type через keyboard (fill інколи не тригерить їх валідатор)
        - чекаємо aria-invalid=false і тільки потім Continue
        """
        p = self.page
        phone = self._normalize_gb_mobile(phone)

        phone_input = p.locator("input#phone[name='phone']").first
        expect(phone_input).to_be_visible(timeout=timeout)

        # фокус через контейнер (з HTML видно що він є)
        container = p.locator("#phone__container").first
        if container.count() > 0:
            container.click(force=True)
        else:
            phone_input.click(force=True)

        # чистимо + друкуємо повільніше
        p.keyboard.press("Control+A")
        p.keyboard.press("Backspace")
        p.keyboard.type(phone, delay=60)

        # 1) sanity що value встановилось (інколи Klarna форматує, тому не завжди 1:1)
        expect(phone_input).not_to_have_value("", timeout=timeout)

        # 2) дочекайся що валідатор прийняв (aria-invalid стає false)
        # якщо атрибут не міняється — хоч би не було "aria-invalid=true"
        try:
            expect(phone_input).to_have_attribute("aria-invalid", "false", timeout=timeout)
        except Exception:
            # fallback: якщо aria-invalid не чіпають, перевіримо що немає error state в контейнері
            pass

        # 3) дуже важлива пауза перед Continue (щоб UI встиг “проковтнути” телефон)
        p.wait_for_timeout(700)

        self._click_continue(timeout)

    def _step_otp(self, otp: str, timeout: int):
        if otp == "999999":
            raise ValueError("OTP 999999 is invalid")

        otp_input = self.page.locator("input#otp_field[name='otp_field']").first
        expect(otp_input).to_be_visible(timeout=timeout)

        otp_input.click(force=True)
        otp_input.fill(otp)

        # Klarna сама переходить далі
        self.page.wait_for_timeout(1200)

    def _step_email(self, email: str | None, timeout: int):
        # email screen може "мигнути" або бути пропущений — не валимось, якщо немає
        email_input = self.page.locator("input#email[name='email']").first

        try:
            email_input.wait_for(state="visible", timeout=3000)  # короткий таймаут
        except PWTimeoutError:
            return  # просто нема email екрана — ок
        if not email:
            email = self._rand_email()
        email_input.click(force=True)
        email_input.fill(email)
        self.page.wait_for_timeout(300)
        self._click_continue(timeout)

    def _step_details(self, first: str, last: str, dob: str, timeout: int):
        p = self.page

        first_name = p.locator("input#given-name[name='given-name']").first
        last_name = p.locator("input#family-name[name='family-name']").first

        # ВАЖЛИВО: details екрана може не бути => короткий таймаут і вихід
        try:
            first_name.wait_for(state="visible", timeout=3000)
        except PWTimeoutError:
            return

        first_name.fill(first)
        last_name.fill(last)

        # DOB — masked (теж optional)
        dob_container = p.locator("#date_of_birth__container").first
        dob_input = p.locator("input#date_of_birth").first
        if dob_container.count() > 0 and dob_input.count() > 0:
            dob_container.click(force=True)
            dob_input.type(dob, delay=40)

        # кнопка може називатися по-різному
        create_btn = p.get_by_role(
            "button",
            name=re.compile(r"create\s+klarna\s+account|continue|next", re.I),
        ).first

        if create_btn.count() > 0:
            create_btn.click(force=True)

        p.wait_for_load_state("domcontentloaded")

    
    def _step_pick_plan(self, timeout: int):
        p = self.page
        btn = p.locator("button[data-testid='pick-plan']").first

        # plan екрана може не бути -> не блокуємо флоу
        try:
            btn.wait_for(state="visible", timeout=3000)
        except PWTimeoutError:
            return

        btn.click(force=True)
        p.wait_for_load_state("domcontentloaded")
        p.wait_for_timeout(500)

    def _step_pay(self, timeout: int):
        p = self.page

        pay_btn = p.locator("button[data-testid='confirm-and-pay'], #buy_button").first
        pay_btn.wait_for(state="visible", timeout=timeout)
        pay_btn.scroll_into_view_if_needed()

        # Дати UI стабілізуватись (Klarna любить micro-animations)
        p.wait_for_timeout(800)

        # Якщо є стан busy/disabled — чекаємо до розумного ліміту
        try:
            expect(pay_btn).to_have_attribute("aria-busy", "false", timeout=15000)
        except Exception:
            pass
        try:
            expect(pay_btn).to_have_attribute("aria-disabled", "false", timeout=15000)
        except Exception:
            pass

        # 1) Спроба клікнути
        try:
            pay_btn.click(timeout=5000, force=True)
            return
        except Exception:
            pass

        # 2) Fallback: Enter (submit)
        # Важливо: треба, щоб фокус був десь у формі/на body, тому клікнемо в кнопку/порожнє місце
        try:
            pay_btn.focus()
        except Exception:
            p.locator("body").click(position={"x": 10, "y": 10})

        # Натискаємо Enter кілька разів з паузами, але без безкінечних циклів
        for _ in range(3):
            p.keyboard.press("Enter")
            p.wait_for_timeout(1000)

            # якщо після Enter кнопка стала busy — значить submit пішов
            try:
                busy = pay_btn.get_attribute("aria-busy")
                if busy == "true":
                    return
            except Exception:
                pass

        # Якщо дійшли сюди — ні клік, ні Enter не тригернули submit
        raise AssertionError("Klarna pay: could not trigger payment (click and Enter both failed).")

    # ---------------- main flow ----------------

    def complete_payment(
        self,
        *,
        phone: str = "+447400123456",
        otp: str = "111111",
        email: str | None = None,
        first_name: str = "Vlad",
        last_name: str = "Ponomarenko",
        dob: str = "11.11.1990",
        timeout: int = 90000,
    ):
        """
        Klarna redirect flow in same tab:
        pay.playground.klarna.com -> login.playground.klarna.com -> ...
        Кроки виконуються лише якщо екран реально є.
        """
        p = self.page
        p.wait_for_load_state("domcontentloaded")

        steps = [
            ("phone", lambda: self._step_phone(phone, timeout)),
            ("otp", lambda: self._step_otp(otp, timeout)),
            ("email", lambda: self._step_email(email, timeout)),
            ("details", lambda: self._step_details(first_name, last_name, dob, timeout)),
            ("plan", lambda: self._step_pick_plan(timeout)),
            ("pay", lambda: self._step_pay(timeout)),
        ]

        for name, fn in steps:
            # якщо вкладка закрилась/редіректнулась — краще вийти, ніж падати в TargetClosed на наступному кроці
            if p.is_closed():
                return

            try:
                fn()
                p.wait_for_timeout(500)
            except PWTimeoutError:
                # цього кроку немає — ок
                continue