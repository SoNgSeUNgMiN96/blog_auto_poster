<?php get_header(); ?>
<section class="listing-head">
  <h1><?php the_archive_title(); ?></h1>
  <?php the_archive_description('<p>', '</p>'); ?>
</section>

<?php if (have_posts()) : ?>
  <section class="post-grid">
    <?php while (have_posts()) : the_post(); ?>
      <?php get_template_part('template-parts/content', 'card'); ?>
    <?php endwhile; ?>
  </section>
  <?php the_posts_pagination(); ?>
<?php else : ?>
  <p>조건에 맞는 게시물이 없습니다.</p>
<?php endif; ?>
<?php get_footer(); ?>
