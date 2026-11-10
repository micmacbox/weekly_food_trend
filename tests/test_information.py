import unittest
from datetime import datetime
from types import SimpleNamespace as NS
from unittest.mock import Mock

from weekly_food.ai import AIError
from weekly_food.core import Evidence, KST, Topic
from weekly_food.guides import make_guide, render_guide
from weekly_food.information import grounded_sources
from weekly_food.pipeline import create_drafts


class InformationTests(unittest.TestCase):
    def test_grounding_keeps_only_supported_segments(self):
        meta = NS(grounding_chunks=[NS(web=NS(uri='https://example.com/faq', title='업체 예약 안내'))],
                  grounding_supports=[NS(segment=NS(text='업체A는 3주 전 예약을 안내합니다.'), grounding_chunk_indices=[0]),
                                      NS(segment=NS(text='출처 없는 추천'), grounding_chunk_indices=[99])])
        sources = grounded_sources(NS(candidates=[NS(grounding_metadata=meta)]), '웨딩케이크')
        self.assertEqual(len(sources), 1)
        self.assertIn('3주', sources[0].summary)
        self.assertNotIn('출처 없는', sources[0].summary)
        self.assertEqual(sources[0].date_precision, 'retrieved')
        with self.assertRaises(AIError):
            grounded_sources(NS(candidates=[]), '웨딩케이크')

    def test_wedding_order_article_is_not_a_recipe_or_missing_field_list(self):
        source = Evidence('예약 FAQ', 'https://example.com/faq', datetime.now(KST).isoformat(),
                          'web_research', '업체A', 'example.com',
                          summary='업체A는 3주 전 예약을 안내합니다. 상담 시 예식일과 인원을 전달합니다. 픽업 시간을 미리 협의합니다.')
        topic = Topic('웨딩케이크', '디저트', [source.id])
        topic.guide_type = 'information'
        writer = Mock()
        writer.json.return_value = {'facts': [
            {'field': key, 'text': text, 'quote': text, 'source_id': source.id}
            for key, text in [('booking', '업체A는 3주 전 예약을 안내합니다.'),
                              ('tips', '상담 시 예식일과 인원을 전달합니다.'),
                              ('logistics', '픽업 시간을 미리 협의합니다.')]]}
        guide = make_guide(topic, [source], writer)
        title, text = render_guide(topic.name, guide)
        self.assertIn('업체A는 3주', text)
        self.assertNotIn('[확인 필요]', text)
        self.assertNotIn('굽기', text)
        self.assertNotIn('## 어디를', text)

    def test_insufficient_information_does_not_produce_an_empty_article(self):
        source = Evidence('소개', 'https://example.com/a', datetime.now(KST).isoformat(), 'blog', '작성자', 'author')
        report = {'topics': [{'name': '마장동 한우', 'category': '음식', 'source_ids': [source.id], 'guide_type': 'information'}],
                  'sources': [source.to_dict()], 'window': {'label': '테스트'}, 'demo': False, 'warnings': []}
        create_drafts(report)
        self.assertEqual(report['drafts'], [])
        self.assertTrue(any('빈 원고' in warning for warning in report['warnings']))
