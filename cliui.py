#!/usr/bin/env python3
"""
Command-line interface for SJTU Running Man app with advanced development options
"""

import sys
import argparse
import getpass
import os
import webbrowser
from src.main import run_sports_upload
from src.api_client import get_authorization_token_and_rules
from src.data_generator import generate_baidu_map_html
from src import login
from utils.auxiliary_util import log_output, SportsUploaderError


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom help formatter that adds more spacing between arguments"""

    def __init__(self, prog, indent_increment=2, max_help_position=48, width=None):
        super().__init__(prog, indent_increment, max_help_position, width)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            # Positional argument
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            # Option argument
            parts = []
            # Add any option strings (like --username, -u)
            parts.extend(action.option_strings)

            # Add metavar if it has one (like USERNAME)
            if action.nargs != 0:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                parts[-1] += f' {args_string}'

            return ', '.join(parts)

    def _format_action(self, action):
        # First, call the parent method to get the original formatted action
        original = super()._format_action(action)

        # Add extra newline after each action to create more spacing
        if action.nargs == argparse.PARSER or action.nargs == argparse.REMAINDER:
            # Don't add extra space for subparsers
            return original
        else:
            # Add an extra newline to create more spacing between options
            return original + '\n'


def progress_callback(current, total, message):
    """Callback function for progress updates"""
    print(f"\rProgress: {current}/{total} - {message}", end="", flush=True)


def log_callback(message, level):
    """Callback function for log messages"""
    if level == "error":
        print(f"[ERROR] {message}")
    elif level == "warning":
        print(f"[WARNING] {message}")
    elif level == "success":
        print(f"[SUCCESS] {message}")
    else:
        print(f"[INFO] {message}")


def stop_check_callback():
    """Callback function to check if operation should be stopped"""
    return False  # For CLI version, we don't implement stopping by default


def main():
    parser = argparse.ArgumentParser(
        description="SJTU Running Man CLI Tool with Advanced Development Options\n",
        formatter_class=CustomHelpFormatter,
        epilog="""
Examples:
  Basic usage: python cliui.py -u <username> -p <password> -d 5.0
  Customize route: python cliui.py --customize-route
  Use custom route: python cliui.py -u <username> -p <password> -d 3.0 -r user
  Custom route file: python cliui.py -u <username> -p <password> -d 5.0 --route-file /path/to/route.txt
  Advanced usage: python cliui.py -u <username> -p <password> -d 3.0 -P 4.0 -c 200 -s 3.0
  Development mode: python cliui.py -u <username> --verify-credentials --verbose
        """
    )

    # Authentication options
    auth_group = parser.add_argument_group('Authentication Options')
    auth_group.add_argument("--username", "-u", help="Student ID/Username for SJTU running system")
    auth_group.add_argument("--password", "-p", help="Password for SJTU running system")

    # Run configuration options
    run_group = parser.add_argument_group('Run Configuration Options')
    run_group.add_argument("--distance", "-d", type=float, default=5.0, help="Target running distance in km (default: 5.0)")
    run_group.add_argument("--hour", "-H", type=int, default=8, help="Run hour (default: 8 for 8:00 AM)")
    run_group.add_argument("--minute", type=int, default=0, help="Run minute (default: 0, use with --hour)")
    run_group.add_argument("--start-date", help="Start date in YYYY-MM-DD format (default: yesterday, uploads backwards from this date)")
    run_group.add_argument("--times", "-t", type=int, default=1, help="Number of days to upload (default: 1)")
    run_group.add_argument("--pace", "-P", type=float, default=3.5, help="Target pace in min/km (default: 3.5 min/km)")

    # Route selection options
    route_group = parser.add_argument_group('Route Options')
    route_group.add_argument("--route", "-r", choices=['default', 'user'], default='default',
                       help="Select route file: 'default' or 'user' (default: 'default')")
    route_group.add_argument("--route-file", help="Custom route file path (overrides --route option)")
    route_group.add_argument("--customize-route", "-C", action="store_true",
                       help="Open browser to customize route graphically")

    # Advanced options
    advanced_group = parser.add_argument_group('Advanced Development Options')
    advanced_group.add_argument("--speed-override", "-s", type=float, help="Override calculated speed in m/s (advanced)")
    advanced_group.add_argument("--compensation", "-c", type=int, default=200, help="Distance compensation in meters (default: 200m)")
    advanced_group.add_argument("--interval", "-i", type=int, default=3, help="Interval between GPS points in seconds (default: 3)")
    advanced_group.add_argument("--min-pace", type=float, default=180, help="Minimum allowed pace in seconds/km (default: 180s/km)")
    advanced_group.add_argument("--max-pace", type=float, default=540, help="Maximum allowed pace in seconds/km (default: 540s/km)")

    # Location options
    location_group = parser.add_argument_group('Location Options')
    location_group.add_argument("--start-lat", type=float, default=31.031599, help="Starting latitude (default: 31.031599)")
    location_group.add_argument("--start-lon", type=float, default=121.442938, help="Starting longitude (default: 121.442938)")
    location_group.add_argument("--end-lat", type=float, default=31.0264, help="Ending latitude (default: 31.0264)")
    location_group.add_argument("--end-lon", type=float, default=121.4551, help="Ending longitude (default: 121.4551)")

    # Debugging options
    debug_group = parser.add_argument_group('Debugging Options')
    debug_group.add_argument("--verify-credentials", action="store_true", help="Verify credentials without uploading")
    debug_group.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    debug_group.add_argument("--debug-mode", action="store_true", help="Enable debug mode with detailed logging")
    debug_group.add_argument("--dry-run", action="store_true", help="Simulate the run without actual upload")

    # API endpoint options
    api_group = parser.add_argument_group('API Endpoint Options (for development/testing)')
    api_group.add_argument("--host", default="pe.sjtu.edu.cn", help="API host (default: pe.sjtu.edu.cn)")
    api_group.add_argument("--uid-url", default="https://pe.sjtu.edu.cn/sports/my/uid", help="UID API URL")
    api_group.add_argument("--my-data-url", default="https://pe.sjtu.edu.cn/sports/my/data", help="My Data API URL")
    api_group.add_argument("--point-rule-url", default="https://pe.sjtu.edu.cn/api/running/point-rule", help="Point Rule API URL")
    api_group.add_argument("--upload-url", default="https://pe.sjtu.edu.cn/api/running/result/upload", help="Upload API URL")

    args = parser.parse_args()

    # Handle route customization first
    if args.customize_route:
        try:
            print("Generating route planning interface...")
            html_file_path = generate_baidu_map_html()
            print(f"Opening route planner in browser: {html_file_path}")

            # Define abs_path in a way that doesn't cause namespace issues
            import os as os_module
            abs_path = os_module.path.abspath(html_file_path)

            print(f"Opening file URL: file://{abs_path}")
            webbrowser.open(f'file://{abs_path}')
            print("Route planner opened in browser. After creating your route:")
            print("1. Click '保存路线' (Save route) button")
            print("2. Save the 'user.txt' file to the project root directory")
            print("3. Run this CLI again with --route user option to use your custom route")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to open route customization: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # Get username and password from command line arguments or prompt
    if not args.username:
        username = input("Enter username (Student ID): ")
    else:
        username = args.username

    if not args.password:
        password = getpass.getpass("Enter password: ")
    else:
        password = args.password

    # Validate credentials if requested
    if args.verify_credentials:
        try:
            log_output("Verifying credentials...", "info")
            
            # First log in using JAccount to get an authenticated session
            print("Logging in via JAccount...")
            session = login.login(username, password)
            if not session:
                print("[ERROR] Failed to log in via JAccount")
                return 1
            print("[SUCCESS] Successfully logged in via JAccount")
            
            # Create a minimal config for validation
            validation_config = {
                'USERNAME': username,
                'PASSWORD': password,
                'USER_ID': username,
                'HOST': args.host,
                'UID_URL': args.uid_url,
                'MY_DATA_URL': args.my_data_url,
                'POINT_RULE_URL': args.point_rule_url,
                'UPLOAD_URL': args.upload_url,
                'START_LONGITUDE': args.start_lon,
                'START_LATITUDE': args.start_lat,
                'RUN_DISTANCE_KM': 1.0,  # Minimal distance for validation
                'RUN_HOUR': 8,
                'RUN_TIMES': 1,
                'INTERVAL_SECONDS': 3,
                'RUNNING_SPEED_MPS': 2.5,
                'SESSION': session  # Add the authenticated session
            }

            # Add route file to validation config
            if args.route_file:
                validation_config['ROUTE_FILE'] = args.route_file
            else:
                validation_config['ROUTE_FILE'] = 'default.txt' if args.route != 'user' else 'user.txt'

            auth_token, rules = get_authorization_token_and_rules(validation_config, log_cb=log_callback)
            if auth_token:
                print(f"[SUCCESS] Credentials verified successfully! Got token: {auth_token[:8]}...")
                return 0
            else:
                print(f"[ERROR] Credentials verification failed: No token received")
                return 1
        except SportsUploaderError as e:
            print(f"[ERROR] Credentials verification failed: {e}")
            return 1
        except Exception as e:
            print(f"[ERROR] Error during credentials verification: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # Calculate or use overridden speed
    if args.speed_override:
        running_speed = args.speed_override
        print(f"[INFO] Using overridden speed: {running_speed} m/s")
    else:
        # Convert pace (min/km) to speed (m/s): 1000m / (pace_in_minutes * 60 seconds)
        running_speed = 1000.0 / (args.pace * 60) if args.pace > 0 else 1000.0 / (3.5 * 60)
        print(f"[INFO] Calculated speed from pace {args.pace} min/km: {running_speed:.3f} m/s")

    # First log in using JAccount to get an authenticated session for the main run
    print("Logging in via JAccount...")
    session = login.login(username, password)
    if not session:
        print("[ERROR] Failed to log in via JAccount")
        return 1
    print("[SUCCESS] Successfully logged in via JAccount")

    # Prepare configuration with advanced options
    config = {
        'USERNAME': username,
        'PASSWORD': password,
        'USER_ID': username,
        'RUN_TIMES': args.times,
        'RUN_HOUR': args.hour,
        'RUN_MINUTE': args.minute,
        'START_DATE': args.start_date,  # Add custom start date
        'RUN_DISTANCE_KM': args.distance,
        'START_LATITUDE': args.start_lat,
        'START_LONGITUDE': args.start_lon,
        'END_LATITUDE': args.end_lat,
        'END_LONGITUDE': args.end_lon,
        'RUNNING_SPEED_MPS': running_speed,
        'INTERVAL_SECONDS': args.interval,
        'HOST': args.host,
        'UID_URL': args.uid_url,
        'MY_DATA_URL': args.my_data_url,
        'POINT_RULE_URL': args.point_rule_url,
        'UPLOAD_URL': args.upload_url,
        'SESSION': session,  # Add the authenticated session
        # Advanced configuration that may be used by data generator
        'MIN_SP_S_PER_KM': args.min_pace,
        'MAX_SP_S_PER_KM': args.max_pace,
        'COMPENSATION_METERS': args.compensation,
        'VERBOSE': args.verbose,
        'DEBUG_MODE': args.debug_mode,
    }

    # Route selection
    if args.route_file:
        # Use custom route file
        import os
        if os.path.exists(args.route_file):
            config['ROUTE_FILE'] = args.route_file
            print(f"[INFO] Using custom route file: {args.route_file}")
        else:
            print(f"[ERROR] Route file does not exist: {args.route_file}")
            return 1
    else:
        # Use selected route type
        if args.route == 'user':
            config['ROUTE_FILE'] = 'user.txt'
            print(f"[INFO] Using user route file: user.txt")
        else:
            config['ROUTE_FILE'] = 'default.txt'
            print(f"[INFO] Using default route file: default.txt")

    print(f"Starting upload for {config['RUN_DISTANCE_KM']} km run(s)")
    print(f"Target pace: {args.pace} min/km (speed: {config['RUNNING_SPEED_MPS']:.2f} m/s)")
    print(f"Compensation: {args.compensation}m")
    print(f"Run hour: {config['RUN_HOUR']}:00")
    print(f"Number of runs: {config['RUN_TIMES']}")
    print(f"Start location: ({args.start_lat}, {args.start_lon})")

    if args.dry_run:
        print("[INFO] Dry run mode - no actual upload will occur")
        return 0

    try:
        success, message = run_sports_upload(
            config,
            progress_callback=progress_callback,
            log_cb=log_callback,
            stop_check_cb=stop_check_callback
        )

        print()  # New line after progress

        if success:
            print(f"[SUCCESS] Upload completed: {message}")
            return 0
        else:
            print(f"[ERROR] Upload failed: {message}")
            return 1

    except KeyboardInterrupt:
        print("\n[INFO] Upload interrupted by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())