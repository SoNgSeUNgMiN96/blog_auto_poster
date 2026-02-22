<?php
if (!defined('ABSPATH')) {
    exit;
}

function ott_trendy_lite_setup(): void {
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('html5', ['search-form', 'comment-form', 'comment-list', 'gallery', 'caption']);

    register_nav_menus([
        'primary' => __('Primary Menu', 'ott-trendy-lite'),
    ]);
}
add_action('after_setup_theme', 'ott_trendy_lite_setup');

function ott_trendy_lite_assets(): void {
    wp_enqueue_style('ott-trendy-lite-main', get_template_directory_uri() . '/assets/css/main.css', [], '1.0.0');
}
add_action('wp_enqueue_scripts', 'ott_trendy_lite_assets');

function ott_trendy_lite_excerpt_length(): int {
    return 28;
}
add_filter('excerpt_length', 'ott_trendy_lite_excerpt_length', 999);

function ott_trendy_lite_excerpt_more($more): string {
    return '...';
}
add_filter('excerpt_more', 'ott_trendy_lite_excerpt_more');

function ott_trendy_lite_comment_callback($comment, $args, $depth): void {
    if (!$comment instanceof WP_Comment) {
        return;
    }
    ?>
    <li <?php comment_class('comment-item'); ?> id="comment-<?php comment_ID(); ?>">
      <article class="comment-card">
        <div class="comment-body"><?php comment_text($comment); ?></div>
        <div class="comment-meta-line">
          <span class="comment-author-name">작성자 - <?php echo esc_html(get_comment_author($comment)); ?></span>
        </div>
        <div class="comment-meta-line">
          <time class="comment-time" datetime="<?php echo esc_attr(get_comment_date('c', $comment)); ?>">
            <?php echo esc_html(get_comment_date('Y.m.d', $comment)); ?>
            ·
            <?php echo esc_html(get_comment_time('H:i', false, false, $comment)); ?>
          </time>
          <?php if ((int) $comment->comment_approved === 0) : ?>
            <span class="comment-pending">승인 대기중</span>
          <?php endif; ?>
        </div>

        <div class="comment-actions">
          <?php
          comment_reply_link(
              array_merge(
                  $args,
                  [
                      'depth' => $depth,
                      'max_depth' => $args['max_depth'] ?? 3,
                      'reply_text' => '답글',
                  ]
              ),
              $comment
          );
          ?>
        </div>
      </article>
    <?php
}
