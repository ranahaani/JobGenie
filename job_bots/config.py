"""
Configuration classes for job applications.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta


@dataclass
class ApplicationConfig:
    """Configuration for job applications."""
    reside_in_barcelona: str
    start_date: str
    expected_compensation: str
    english_proficiency: str
    require_sponsorship: str
    react_experience: str
    skills: List[str]
    german_proficiency: str
    current_city: str
    remotely_available: str
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ApplicationConfig':
        """Load configuration from a JSON file.
        
        Args:
            file_path: Path to the JSON config file
            
        Returns:
            ApplicationConfig instance
        """
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        
        # Update start date to be 15 days from now
        current_start_date = datetime.now()
        new_start_date = current_start_date + timedelta(days=15)
        config_dict['start_date'] = new_start_date.strftime("%d-%m-%Y")
        
        return cls(**config_dict)
    
    def to_file(self, file_path: str) -> None:
        """Save configuration to a JSON file.
        
        Args:
            file_path: Path to save the JSON config
        """
        # Convert to dictionary
        config_dict = {
            'reside_in_barcelona': self.reside_in_barcelona,
            'start_date': self.start_date,
            'expected_compensation': self.expected_compensation,
            'english_proficiency': self.english_proficiency,
            'require_sponsorship': self.require_sponsorship,
            'react_experience': self.react_experience,
            'skills': self.skills,
            'german_proficiency': self.german_proficiency,
            'current_city': self.current_city,
            'remotely_available': self.remotely_available,
        }
        
        with open(file_path, 'w') as f:
            json.dump(config_dict, f, indent=2)


@dataclass
class PlatformConfig:
    """Platform-specific configuration."""
    platform_name: str
    login_url: Optional[str] = None
    cookies_file: Optional[str] = None
    api_key: Optional[str] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load_all_platforms(cls) -> Dict[str, 'PlatformConfig']:
        """Load configurations for all supported platforms.
        
        Returns:
            Dictionary mapping platform names to PlatformConfig instances
        """
        platforms = {}
        
        # Join.com configuration
        platforms['join'] = PlatformConfig(
            platform_name='join',
            login_url='https://join.com/auth/login',
            cookies_file='cookies.json',
        )
        
        # Greenhouse configuration
        platforms['greenhouse'] = PlatformConfig(
            platform_name='greenhouse',
            # Greenhouse doesn't typically require login for applications
            custom_settings={
                'use_analyzer': True,
            }
        )
        
        return platforms 