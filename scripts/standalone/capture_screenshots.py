#!/usr/bin/env python3
"""
Capture screenshots of VistterStream application for documentation
"""
import asyncio
from playwright.async_api import async_playwright
import os

async def capture_screenshots():
    screenshots_dir = "docs/screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        base_url = "http://192.168.12.107:3000"
        
        # Login first
        await page.goto(f"{base_url}/login")
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path=f"{screenshots_dir}/00-login.png", full_page=True)
        
        # Fill login form
        await page.fill('input[type="text"]', "admin")
        await page.fill('input[type="password"]', "admin")
        await page.click('button:has-text("Sign in")')
        await page.wait_for_url("**/dashboard")
        await page.wait_for_timeout(2000)
        
        # Dashboard
        await page.screenshot(path=f"{screenshots_dir}/01-dashboard.png", full_page=True)
        
        # Cameras
        await page.goto(f"{base_url}/cameras")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{screenshots_dir}/02-cameras.png", full_page=True)
        
        # Streams
        await page.goto(f"{base_url}/streams")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{screenshots_dir}/03-streams.png", full_page=True)
        
        # Timelines
        await page.goto(f"{base_url}/timelines")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{screenshots_dir}/04-timelines.png", full_page=True)
        
        # Scheduler
        await page.goto(f"{base_url}/scheduler")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{screenshots_dir}/05-scheduler.png", full_page=True)
        
        # Settings - General
        await page.goto(f"{base_url}/settings")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{screenshots_dir}/06-settings-general.png", full_page=True)
        
        # Settings - Account  
        await page.click('button:has-text("Account")', timeout=5000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{screenshots_dir}/07-settings-account.png", full_page=True)
        
        # Settings - PTZ Presets
        await page.click('button:has-text("PTZ Presets")', timeout=5000)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{screenshots_dir}/08-settings-ptz-presets.png", full_page=True)
        
        # Settings - Assets
        await page.click('button:has-text("Assets")', timeout=5000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{screenshots_dir}/09-settings-assets.png", full_page=True)
        
        # Settings - Destinations
        await page.click('button:has-text("Destinations")', timeout=5000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{screenshots_dir}/10-settings-destinations.png", full_page=True)
        
        # Settings - System
        await page.click('button:has-text("System")', timeout=5000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{screenshots_dir}/11-settings-system.png", full_page=True)
        
        await browser.close()
        print("✓ All screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_screenshots())

