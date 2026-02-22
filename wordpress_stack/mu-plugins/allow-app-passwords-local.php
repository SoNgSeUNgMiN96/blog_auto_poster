<?php
/**
 * Plugin Name: Allow Application Passwords on Local HTTP
 * Description: Enable WordPress Application Passwords for local/dev environments without HTTPS.
 */

if (!defined('ABSPATH')) {
    exit;
}

add_filter('wp_is_application_passwords_available', '__return_true');
add_filter('wp_is_application_passwords_available_for_user', '__return_true', 10, 2);
