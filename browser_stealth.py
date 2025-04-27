#!/usr/bin/env python3
"""
Advanced Browser Stealth Module

This module provides comprehensive browser fingerprint randomization and
anti-detection measures for Selenium WebDriver.
"""

import random
import json
import time
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent

class StealthConfig:
    """Configuration for browser stealth settings."""
    
    # Common screen resolutions
    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864),
        (1440, 900), (1280, 720), (1600, 900)
    ]
    
    # Common color depths
    COLOR_DEPTHS = [24, 32]
    
    # Common platforms by OS
    PLATFORMS = {
        'win': ['Win32', 'Win64', 'Windows', 'WinNT'],
        'mac': ['MacIntel', 'MacPPC', 'Macintosh', 'MacM1'],
        'linux': ['Linux x86_64', 'Linux armv7l', 'Linux aarch64']
    }
    
    # Common hardware concurrency values
    HARDWARE_CONCURRENCY = [2, 4, 6, 8, 12, 16]
    
    # Common device memory values (in GB)
    DEVICE_MEMORY = [2, 4, 8, 16]
    
    # WebGL vendors and renderers
    WEBGL_VENDORS = ['Google Inc.', 'Intel Inc.', 'NVIDIA Corporation', 'AMD']
    WEBGL_RENDERERS = [
        'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)',
        'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)',
        'ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0)'
    ]

class BrowserStealth:
    """Implements advanced browser stealth techniques."""
    
    def __init__(self, use_proxy: bool = True):
        """Initialize stealth configuration.
        
        Args:
            use_proxy: Whether to enable proxy support
        """
        self.use_proxy = use_proxy
        self.user_agent = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self._generate_profile()
    
    def _generate_profile(self) -> None:
        """Generate a consistent device profile."""
        # Select random OS platform
        self.os_type = random.choice(['win', 'mac', 'linux'])
        self.platform = random.choice(StealthConfig.PLATFORMS[self.os_type])
        
        # Generate consistent device characteristics
        self.screen_resolution = random.choice(StealthConfig.SCREEN_RESOLUTIONS)
        self.color_depth = random.choice(StealthConfig.COLOR_DEPTHS)
        self.hardware_concurrency = random.choice(StealthConfig.HARDWARE_CONCURRENCY)
        self.device_memory = random.choice(StealthConfig.DEVICE_MEMORY)
        
        # Generate WebGL characteristics
        self.webgl_vendor = random.choice(StealthConfig.WEBGL_VENDORS)
        self.webgl_renderer = random.choice(StealthConfig.WEBGL_RENDERERS)
    
    def _get_stealth_js(self) -> str:
        """Generate JavaScript code for browser fingerprint modification."""
        return """
        // Override property getters
        const overrides = {
            platform: '%s',
            hardwareConcurrency: %d,
            deviceMemory: %d,
            userAgent: '%s',
            screenResolution: [%d, %d],
            colorDepth: %d
        };
        
        // Override navigator properties
        for (const [key, value] of Object.entries(overrides)) {
            if (Object.getOwnPropertyDescriptor(Navigator.prototype, key)) {
                Object.defineProperty(Navigator.prototype, key, {
                    get: () => value
                });
            } else {
                Object.defineProperty(navigator, key, {
                    get: () => value
                });
            }
        }
        
        // Override WebGL fingerprinting
        const getParameterProxyHandler = {
            apply: function(target, thisArg, argumentsList) {
                const param = argumentsList[0];
                
                // WebGL vendor and renderer strings
                if (param === 37445) {
                    return '%s'; // vendor
                }
                if (param === 37446) {
                    return '%s'; // renderer
                }
                
                return target.apply(thisArg, argumentsList);
            }
        };
        
        // Apply WebGL proxy
        if (WebGLRenderingContext.prototype.getParameter) {
            WebGLRenderingContext.prototype.getParameter = new Proxy(
                WebGLRenderingContext.prototype.getParameter,
                getParameterProxyHandler
            );
        }
        
        // Randomize canvas fingerprint
        const oldGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
            const context = oldGetContext.call(this, contextType, contextAttributes);
            if (context && contextType === '2d') {
                const oldFillText = context.fillText;
                context.fillText = function(...args) {
                    const txt = args[0];
                    const x = args[1];
                    const y = args[2];
                    
                    // Add subtle noise to the text position
                    const noiseX = (Math.random() - 0.5) * 0.5;
                    const noiseY = (Math.random() - 0.5) * 0.5;
                    
                    return oldFillText.call(this, txt, x + noiseX, y + noiseY);
                };
            }
            return context;
        };
        
        // Override AudioContext
        const oldAudioContext = window.AudioContext || window.webkitAudioContext;
        if (oldAudioContext) {
            window.AudioContext = window.webkitAudioContext = function(...args) {
                const context = new oldAudioContext(...args);
                const oldCreateOscillator = context.createOscillator;
                context.createOscillator = function(...args) {
                    const oscillator = oldCreateOscillator.call(this, ...args);
                    // Add subtle randomization to frequency
                    const oldFrequency = oscillator.frequency;
                    Object.defineProperty(oscillator, 'frequency', {
                        get: () => oldFrequency * (1 + (Math.random() - 0.5) * 0.01)
                    });
                    return oscillator;
                };
                return context;
            };
        }
        """ % (
            self.platform,
            self.hardware_concurrency,
            self.device_memory,
            self.user_agent.random,
            self.screen_resolution[0],
            self.screen_resolution[1],
            self.color_depth,
            self.webgl_vendor,
            self.webgl_renderer
        )
    
    def configure_options(self, options: Optional[Options] = None) -> Options:
        """Configure Chrome options with stealth settings.
        
        Args:
            options: Existing Chrome options to modify (creates new if None)
            
        Returns:
            Modified Chrome options
        """
        if options is None:
            options = Options()
        
        # Basic anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Additional stealth options
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-save-password-bubble')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        
        # Set random window size
        options.add_argument(f'--window-size={self.screen_resolution[0]},{self.screen_resolution[1]}')
        
        # Set random user agent
        options.add_argument(f'--user-agent={self.user_agent.random}')
        
        # Add WebGL vendor
        options.add_argument(f'--gpu-vendor={self.webgl_vendor}')
        
        return options
    
    def apply_stealth_patches(self, driver: webdriver.Chrome) -> None:
        """Apply stealth patches to a running Chrome instance.
        
        Args:
            driver: Chrome WebDriver instance
        """
        # Inject stealth JavaScript
        driver.execute_script(self._get_stealth_js())
        
        # Mask WebDriver presence
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        try:
            # Set permissions with proper origin
            driver.get("about:blank")  # Navigate to a valid page first
            driver.execute_cdp_cmd('Browser.grantPermissions', {
                'origin': 'https://www.google.com',  # Set specific origin
                'permissions': [
                    'geolocation',
                    'notifications'
                ]
            })
        except Exception as e:
            # Log error but continue if permission setting fails
            print(f"Warning: Could not set permissions: {e}")
    
    def simulate_human_behavior(self, driver: webdriver.Chrome) -> None:
        """Simulate realistic human behavior patterns.
        
        Args:
            driver: Chrome WebDriver instance
        """
        # Simulate natural scrolling
        driver.execute_script("""
            function naturalScroll() {
                const maxScroll = Math.max(
                    document.documentElement.scrollHeight,
                    document.body.scrollHeight
                );
                let currentScroll = 0;
                const scrollInterval = setInterval(() => {
                    if (currentScroll >= maxScroll) {
                        clearInterval(scrollInterval);
                        return;
                    }
                    const step = Math.floor(Math.random() * 100) + 50;
                    window.scrollBy(0, step);
                    currentScroll += step;
                    
                    // Random pause
                    if (Math.random() < 0.1) {
                        clearInterval(scrollInterval);
                        setTimeout(naturalScroll, Math.random() * 1000 + 500);
                    }
                }, Math.random() * 100 + 100);
            }
            naturalScroll();
        """)
        
        # Random mouse movements
        driver.execute_script("""
            function simulateMouseMovement() {
                const points = [];
                const numPoints = Math.floor(Math.random() * 10) + 5;
                
                // Generate random points
                for (let i = 0; i < numPoints; i++) {
                    points.push({
                        x: Math.random() * window.innerWidth,
                        y: Math.random() * window.innerHeight
                    });
                }
                
                let currentPoint = 0;
                const moveInterval = setInterval(() => {
                    if (currentPoint >= points.length) {
                        clearInterval(moveInterval);
                        return;
                    }
                    
                    const event = new MouseEvent('mousemove', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: points[currentPoint].x,
                        clientY: points[currentPoint].y
                    });
                    document.dispatchEvent(event);
                    currentPoint++;
                }, Math.random() * 100 + 50);
            }
            simulateMouseMovement();
        """)
        
        # Random focus/blur events
        driver.execute_script("""
            function simulateFocusEvents() {
                const elements = document.querySelectorAll('a, button, input, select');
                if (elements.length === 0) return;
                
                setInterval(() => {
                    if (Math.random() < 0.3) {
                        const element = elements[Math.floor(Math.random() * elements.length)];
                        element.focus();
                        setTimeout(() => element.blur(), Math.random() * 1000 + 500);
                    }
                }, Math.random() * 2000 + 1000);
            }
            simulateFocusEvents();
        """) 
