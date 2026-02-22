<article <?php post_class('post-card'); ?> id="post-<?php the_ID(); ?>">
  <a class="post-card-link" href="<?php the_permalink(); ?>">
    <?php if (has_post_thumbnail()) : ?>
      <div class="thumb-wrap"><?php the_post_thumbnail('medium_large'); ?></div>
    <?php endif; ?>
    <div class="post-body">
      <h2 class="post-title"><?php the_title(); ?></h2>
      <p class="post-meta"><?php echo esc_html(get_the_date('Y.m.d')); ?></p>
      <p class="post-excerpt"><?php echo esc_html(get_the_excerpt()); ?></p>
    </div>
  </a>
</article>
