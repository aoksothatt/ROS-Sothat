# ROS Sothat — Design System & Page Specifications
**Document ID:** `02_design_and_page_structure.md`  
**System:** ROS Sothat Private Server Platform  
**Target:** Website Frontend Application (`ros-website`)  
**Date:** November 2026  
**Status:** IMPLEMENTED & AUDITED  

---

## 1. Visual Design System

The visual identity is modeled around a dark tactical survival aesthetic appropriate for a private multiplayer community playing Rules of Survival Legacy. The interface deliberately avoids corporate administrative templates, excessive glassmorphism, or cartoon banners.

### 1.1 Color Palette

| Token Name | Hex Code | Purpose / Usage |
| :--- | :--- | :--- |
| `--bg-primary` | `#080B10` | Main application backdrop; deep tactical navy-black |
| `--bg-secondary` | `#101720` | Secondary backgrounds, navbar, footer, inputs |
| `--bg-card` | `#151E29` | Container card and panel background |
| `--bg-card-hover` | `#1A2634` | Hover highlight on clickable cards and secondary buttons |
| `--text-primary` | `#F3F6FA` | Primary headings, prominent values, labels |
| `--text-secondary` | `#9AA7B5` | Body copy, secondary descriptions, metadata |
| `--text-muted` | `#64748B` | Subtle disclaimers, timestamps, placeholders |
| `--accent-gold` | `#D7A84B` | Primary call-to-action buttons, active badges, key highlights |
| `--accent-gold-hover` | `#E5B85C` | CTA hover state, active links |
| `--accent-red` | `#B94B3C` | Combat tags, logout buttons, error indicators |
| `--border-color` | `#263442` | Card outlines, input borders, structural dividers |
| `--border-focus` | `#D7A84B` | Input focus ring and card hover borders |
| `--success` | `#34D399` | Online status indicators, successful alert states |

### 1.2 Typography & Hierarchy
- **Heading Font:** Condensed heavy sans-serif (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, Arial) styled with bold weights (`800`–`900`), uppercase transforms, and letter spacing (`0.05em`–`0.12em`).
- **Body Font:** Clean, highly readable system sans-serif with comfortable line height (`1.6`).
- **Monospace Font:** `SF Mono`, `Consolas`, Menlo for OTP input digits and technical telemetry.

---

## 2. Page Specifications & Section Layout

### 2.1 Landing Page (`HomePage.vue` — Route `/`)
- **Sticky Navbar:** Features the ROS Sothat wordmark with `P03` badge, direct jump links (`About`, `Features`, `Announcements`, `Download`), dynamic auth buttons (`Dashboard` / `Logout` if authenticated; `Login` / `Join Island` if guest), and a responsive mobile collapse menu.
- **Hero Section:**
  - Headline: `"THE ISLAND IS WAITING."` with gold glow styling.
  - Subtitle: `"A private Rules of Survival Legacy community. Survive together, compete together, and build your own battlefield."`
  - CTAs: Primary `"JOIN THE COMMUNITY"` (`/register`) and Secondary `"EXPLORE ROS SOTHAT"` (`/#about`).
  - Stat Badges: 10–20 Invited Friends, 100% Independent Server, Legacy Engine.
- **About Section:** Clarifies that the original iOS client archive is preserved and we are building the private server and community platform around it; outlines invite-only principles and modern passwordless security.
- **Roadmap & Features Grid:** Visual cards for Private Community (Active), Email OTP (Active), Diamond Ledger (Backend Ready), Inventory System (Backend Ready), Mercury Gateway (In Development), and iOS Companion Launcher (In Development).
- **Announcements Section:** Development updates formatted with category badges, timestamps, and brief summaries.
- **Download Section:** Clearly states that client distribution is in preparation; explains Ad Hoc distribution requirements and prevents fake download links.
- **Footer:** Community disclaimers, development status indicator, and navigation links.

### 2.2 Registration Page (`RegisterPage.vue` — Route `/register`)
- **Step 1 (Email Request):** Input field for player email, optional input for chosen nickname, and `"Send Verification Code"` CTA with 60-second cooldown timer.
- **Step 2 (OTP Verification):** Displays target masked email (`p***r@domain.com`), 6-box interactive `OtpInput` component with auto-focus, paste support, and backspace navigation, `"Verify & Register"` button, and countdown-enforced resend option.
- **Error Handling:** Displays server feedback (409 Conflict if email is taken, 429 if cooldown active, 422 if invalid email format).

### 2.3 Login Page (`LoginPage.vue` — Route `/login`)
- **Dual-Mode Toggle:**
  1. **Email OTP (Player):** Passwordless 6-digit verification code workflow identical to registration.
  2. **Admin Password (Server Operator):** Traditional username and password inputs for administrators, communicating directly with `/api/v1/account/login`.
- **Protection Responses:** Explicit feedback for banned accounts (`Account is banned. Reason: ...`), invalid codes with attempt counters remaining, and generic responses for unknown emails.

### 2.4 Protected Dashboard (`DashboardPage.vue` — Route `/dashboard`)
- **Navigation Guard:** Inaccessible to unauthenticated guests; redirects to `/login?redirect=/dashboard`.
- **Operator Profile Banner:** Dynamic avatar insignia derived from username, active role badge (`PLAYER` / `ADMIN`), operator status (`ACTIVE OPERATOR` / `SUSPENDED`), and email.
- **Verified Telemetry Cards:**
  - Account Identifier (`#<id>`)
  - Account Registered Date (formatted timestamp)
  - Last Authenticated Date (formatted timestamp)
  - Game Character Link (`PROVISIONED` / `UNASSIGNED`)
- **In-Development Capability Placeholders:** Dashed tactical cards outlining future capabilities: Diamond Currency Vault, Tactical Armory & Inventory, Matchmaking Records, and iOS Companion Launcher.
- **Logout Action:** Securely terminates session, wipes `sessionStorage`, and redirects to `/login`.

### 2.5 404 Not Found Page (`NotFoundPage.vue` — Route `/404`)
- Tactical error layout: `"SECTOR ERROR 404"`, `"COORDINATES NOT FOUND"`, with return-to-base navigation button.

---

## 3. Responsive Breakpoint Matrix

The layout is tested and fully responsive across all standard viewports without horizontal scrollbars:

| Device Category | Target Viewport | Breakpoint Behaviors |
| :--- | :--- | :--- |
| **Desktop Ultra** | `1920 × 1080` | Max container width `1200px`; centered grids (3 columns). |
| **Desktop Standard** | `1440 × 900` | Balanced grid cards; full navigation links visible. |
| **Tablet Portrait** | `768 × 1024` | 2-column feature grids; footer converts to 2x2 layout. |
| **Mobile Standard** | `390 × 844` (iPhone 12/13/14) | Navigation collapses into mobile hamburger menu; OTP boxes shrink to `44px`; hero title resizes to `2.25rem`. |
| **Mobile Compact** | `375 × 667` (iPhone SE) | Single-column form containers; OTP boxes shrink to `40px`; touch targets maintained at $\ge 44\text{px}$. |
