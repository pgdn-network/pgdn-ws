# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-21

### Added
- **Rate Limiting Support**: Comprehensive rate limiting system to prevent notification spam
  - In-memory token bucket rate limiting (default)
  - Redis-backed sliding window rate limiting for distributed systems
  - YAML and environment variable configuration support
  - Per-notification-type rate limit configuration
  - Automatic rate limit checking in core `notify()` function
  - Comprehensive test coverage for all rate limiting features
- Configuration loading system (`pgdn_notify.config`)
- Rate limiting management (`pgdn_notify.rate_limit`)
- Example configuration files and JSON examples
- Support for PyYAML as optional dependency

### Enhanced
- Core `notify()` function now includes automatic rate limit checking
- Setup.py updated with new optional dependencies (`redis`, `yaml`, `all`)
- README.md with comprehensive rate limiting documentation
- Test suite expanded with rate limiting tests

### Dependencies
- Added optional dependency: `PyYAML>=5.4.0` for YAML configuration support
- Existing optional dependency: `redis>=4.0.0` for Redis-backed rate limiting

## [0.1.0] - 2025-01-21

### Added
- Initial release of pgdn-ws
- Core notification system with unified `notify()` interface
- Support for 4 notification types:
  - Slack (via webhooks)
  - Email (via SMTP)
  - Webhooks (HTTP POST)
  - Websockets (Redis pub/sub)
- Command-line interface (`pgdn-ws`)
- Comprehensive test suite
- Extensible architecture for adding new notification types
- Standardized JSON input/output schemas
- MIT License 