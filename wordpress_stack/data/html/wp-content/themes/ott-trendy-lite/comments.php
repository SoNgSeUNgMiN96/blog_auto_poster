<?php
if (post_password_required()) {
    return;
}
?>
<div id="comments" class="comments-area">
  <?php if (have_comments()) : ?>
    <h2 class="comments-title">댓글 <?php echo esc_html(get_comments_number()); ?>개</h2>
    <ol class="comment-list">
      <?php
      wp_list_comments([
          'style' => 'ol',
          'short_ping' => true,
          'callback' => 'ott_trendy_lite_comment_callback',
      ]);
      ?>
    </ol>
    <?php the_comments_pagination(); ?>
  <?php endif; ?>

  <?php
  comment_form([
      'title_reply' => '댓글 남기기',
      'label_submit' => '등록',
      'class_submit' => 'comment-submit',
      'comment_field' => '<p class="comment-form-comment"><label for="comment">댓글</label><textarea id="comment" name="comment" cols="45" rows="5" required></textarea></p>',
      'fields' => [
          'author' => '<p class="comment-form-author"><label for="author">이름</label><input id="author" name="author" type="text" required /></p>',
          'email'  => '<p class="comment-form-email"><label for="email">이메일</label><input id="email" name="email" type="email" required /></p>',
          'url'    => '<p class="comment-form-url"><label for="url">웹사이트 (선택)</label><input id="url" name="url" type="url" /></p>',
      ],
  ]);
  ?>
</div>
