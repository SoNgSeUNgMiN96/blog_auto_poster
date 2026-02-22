<?php if (!defined('ABSPATH')) { exit; } ?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
  <meta charset="<?php bloginfo('charset'); ?>">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="<?php echo esc_url(home_url('/')); ?>">
      <span class="brand-dot"></span>
      <span><?php bloginfo('name'); ?></span>
    </a>
    <nav class="top-nav" aria-label="Primary Navigation">
      <?php wp_nav_menu([
          'theme_location' => 'primary',
          'container' => false,
          'fallback_cb' => false,
      ]); ?>
    </nav>
    <div class="header-search"><?php get_search_form(); ?></div>
  </div>
</header>
<main class="site-main wrap">
