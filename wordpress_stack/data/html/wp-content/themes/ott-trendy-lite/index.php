<?php get_header(); ?>
<section class="listing-head">
  <h1><?php echo esc_html(get_bloginfo('name')); ?></h1>
  <p><?php echo esc_html(get_bloginfo('description')); ?></p>
</section>

<?php if (have_posts()) : ?>
  <section class="post-grid">
    <?php while (have_posts()) : the_post(); ?>
      <?php get_template_part('template-parts/content', 'card'); ?>
    <?php endwhile; ?>
  </section>
  <?php the_posts_pagination(); ?>
<?php else : ?>
  <p>아직 게시물이 없습니다.</p>
<?php endif; ?>
<?php get_footer(); ?>
