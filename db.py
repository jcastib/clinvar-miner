import sqlite3
from sqlite3 import OperationalError

class DB():
    def __init__(self):
        self.db = sqlite3.connect('clinvar.db', timeout=20)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()

    def max_date(self):
        return list(self.cursor.execute('SELECT MAX(date) FROM submissions'))[0][0]

    def old_significance_term_info(self):
        return list(map(
            dict,
            self.cursor.execute('''
                SELECT * FROM (
                    SELECT significance, MIN(date) AS first_seen, MAX(date) AS last_seen FROM submissions
                    GROUP BY significance ORDER BY significance
                ) WHERE last_seen!=(SELECT MAX(date) FROM submissions)
            ''')
        ))

    def significance_term_info(self):
        return list(map(
            dict,
            self.cursor.execute('''
                SELECT significance, MIN(date) AS first_seen FROM submissions
                GROUP BY significance ORDER BY significance
            ''')
        ))

    def submissions(self, gene = None, variant_name = None, min_stars = 0, standardized_method = None,
                    min_conflict_level = 0):
        query = '''
            SELECT DISTINCT
                variant_name,
                gene,
                submitter1_id AS submitter_id,
                submitter1_name AS submitter_name,
                rcv1 AS rcv,
                scv1 AS scv,
                significance1 AS significance,
                last_eval1 AS last_eval,
                review_status1 AS review_status,
                trait1_db AS trait_db,
                trait1_id AS trait_id,
                trait1_name AS trait_name,
                method1 AS method,
                comment1 AS comment
            FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if gene:
            query += ' AND gene=:gene'

        if variant_name:
            query += ' AND variant_name=:variant_name'

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' ORDER BY submitter_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'gene': gene,
                    'variant_name': variant_name,
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))

    def submitter_info(self, submitter_id):
        try:
            return dict(list(self.cursor.execute('SELECT * from submitter_info WHERE id=:id', [submitter_id]))[0])
        except (IndexError, OperationalError):
            return {'id': int(submitter_id), 'name': submitter_id}

    def submitter_primary_method(self, submitter_id):
        return list(
            self.cursor.execute('''
                SELECT method FROM current_submissions WHERE submitter_id=?
                GROUP BY method ORDER BY COUNT(*) DESC LIMIT 1
            ''', [submitter_id])
        )[0][0]

    def total_conflicting_variants_by_significance_and_significance(self, submitter1_id = None, submitter2_id = None,
                                                                    min_stars1 = 0, min_stars2 = 0,
                                                                    standardized_method1 = None,
                                                                    standardized_method2 = None,
                                                                    standardized_terms = False):
        if standardized_terms:
            query = 'SELECT standardized_significance1 AS significance1, standardized_significance2 AS significance2'
        else:
            query = 'SELECT significance1, significance2'

        query += ', COUNT(DISTINCT variant_name) AS count FROM current_comparisons'

        query += ' WHERE star_level1>=:min_stars1 AND star_level2>=:min_stars2 AND conflict_level>=1'

        if submitter1_id:
            query += ' AND submitter1_id=:submitter1_id'

        if submitter2_id:
            query += ' AND submitter2_id=:submitter2_id'

        if standardized_method1:
            query += ' AND standardized_method1=:standardized_method1'

        if standardized_method2:
            query += ' AND standardized_method2=:standardized_method2'

        if standardized_terms:
            query += ' GROUP BY standardized_significance1, standardized_significance2'
        else:
            query += ' GROUP BY significance1, significance2'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'submitter1_id': submitter1_id,
                    'submitter2_id': submitter2_id,
                    'min_stars1': min_stars1,
                    'min_stars2': min_stars2,
                    'standardized_method1': standardized_method1,
                    'standardized_method2': standardized_method2,
                }
            )
        ))

    def total_conflicting_variants_by_submitter(self, submitter1_id = None, min_stars1 = 0, min_stars2 = 0,
                                                standardized_method1 = None, standardized_method2 = None):
        if submitter1_id:
            query = 'SELECT submitter2_id AS submitter_id, submitter2_name AS submitter_name'
        else:
            query = 'SELECT submitter1_id AS submitter_id, submitter1_name AS submitter_name'

        query += '''
            , COUNT(DISTINCT variant_name) AS count
            FROM current_comparisons
            WHERE star_level1>=:min_stars1 AND star_level2>=:min_stars2 AND conflict_level>=1
        '''

        if submitter1_id:
            query += ' AND submitter1_id=:submitter1_id'

        if standardized_method1:
            query += ' AND standardized_method1=:standardized_method1'

        if standardized_method2:
            query += ' AND standardized_method2=:standardized_method2'

        query += ' GROUP BY submitter_id ORDER BY submitter_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'submitter1_id': submitter1_id,
                    'min_stars1': min_stars1,
                    'min_stars2': min_stars2,
                    'standardized_method1': standardized_method1,
                    'standardized_method2': standardized_method2,
                }
            )
        ))

    def total_conflicting_variants_by_submitter_and_conflict_level(self, submitter1_id, min_stars1 = 0, min_stars2 = 0,
                                                                   standardized_method1 = None,
                                                                   standardized_method2 = None):
        query = '''
            SELECT
                submitter2_id AS submitter_id,
                submitter2_name AS submitter_name,
                conflict_level,
                COUNT(DISTINCT variant_name) AS count
            FROM current_comparisons
            WHERE
                submitter1_id=:submitter1_id AND
                star_level1>=:min_stars1 AND
                star_level2>=:min_stars2 AND
                conflict_level>=1
        '''

        if standardized_method1:
            query += ' AND standardized_method1=:standardized_method1'

        if standardized_method2:
            query += ' AND standardized_method2=:standardized_method2'

        query += ' GROUP BY submitter2_id, conflict_level ORDER BY submitter2_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'submitter1_id': submitter1_id,
                    'min_stars1': min_stars1,
                    'min_stars2': min_stars2,
                    'standardized_method1': standardized_method1,
                    'standardized_method2': standardized_method2,
                }
            )
        ))

    def total_significance_terms(self, term):
        return list(map(
            dict,
            self.cursor.execute('''
                SELECT submitter_id, submitter_name, COUNT(*) AS count FROM current_submissions WHERE significance=?
                GROUP BY submitter_id ORDER BY submitter_name
            ''', [term])
        ))

    def total_significance_terms_over_time(self):
        return list(map(
            dict,
            self.cursor.execute('SELECT date, COUNT(DISTINCT significance) AS count FROM submissions GROUP BY date')
        ))

    def total_submissions_by_country(self):
        return list(map(
            dict,
            self.cursor.execute('''
                SELECT country, country_code, COUNT(*) AS count FROM current_submissions
                LEFT JOIN submitter_info ON current_submissions.submitter_id=submitter_info.id
                GROUP BY country ORDER BY country
            ''')
        ))

    def total_submissions_by_method(self, min_stars = 0, min_conflict_level = 0):
        return list(map(
            dict,
            self.cursor.execute(
                '''
                    SELECT method1 AS method, COUNT(DISTINCT scv1) AS count
                    FROM current_comparisons
                    WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
                    GROUP BY method ORDER BY method
                ''',
                {
                    'min_stars': min_stars,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))

    def total_submissions_by_standardized_method_over_time(self, min_stars = 0, min_conflict_level = 0):
        return list(map(
            dict,
            self.cursor.execute(
                '''
                    SELECT date, standardized_method1 AS standardized_method, COUNT(DISTINCT scv1) AS count
                    FROM comparisons
                    WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
                    GROUP BY date, standardized_method ORDER BY date, count DESC
                ''',
                {
                    'min_stars': min_stars,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))

    def total_submissions_by_submitter(self, country = None, min_conflict_level = 0):
        query = '''
            SELECT submitter1_id AS submitter_id, submitter1_name AS submitter_name, COUNT(DISTINCT scv1) AS count
            FROM current_comparisons
        '''

        if country:
            query += ' LEFT JOIN submitter_info ON current_comparisons.submitter1_id=submitter_info.id'

        query += ' WHERE conflict_level>=:min_conflict_level'

        if country:
            query += ' AND country=:country'

        query += ' GROUP BY submitter1_id ORDER BY submitter1_name'

        return list(map(
            dict,
            self.cursor.execute(query, {'country': country, 'min_conflict_level': min_conflict_level})
        ))

    def total_submissions_by_variant(self, gene = None, trait_name = None, submitter_id = None, significance = None,
                                     min_stars = 0, standardized_method = None, min_conflict_level = 0,
                                     standardized_terms = False):
        query = '''
            SELECT variant_name, COUNT(DISTINCT scv1) AS count FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if gene:
            query += ' AND gene=:gene'

        if trait_name:
            query += ' AND UPPER(trait1_name)=:trait_name'

        if submitter_id:
            query += ' AND submitter1_id=:submitter_id'

        if standardized_terms:
            query += ' AND standardized_significance1=:significance'
        else:
            query += ' AND significance1=:significance'

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY variant_name ORDER BY variant_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'gene': gene,
                    'trait_name': trait_name,
                    'significance': significance,
                    'submitter_id': submitter_id,
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))

    def total_variants(self, gene = None, submitter1_id = None, submitter2_id = None, trait_name = None, min_stars1 = 0,
                       min_stars2 = 0, standardized_method1 = None, standardized_method2 = None,
                       min_conflict_level = 0):
        query = '''
            SELECT COUNT(DISTINCT variant_name) FROM current_comparisons
            WHERE star_level1>=:min_stars1 AND star_level2>=:min_stars2 AND conflict_level>=:min_conflict_level
        '''

        if gene:
            query += ' AND gene=:gene'

        if submitter1_id:
            query += ' AND submitter1_id=:submitter1_id'

        if submitter2_id:
            query += ' AND submitter2_id=:submitter2_id'

        if trait_name:
            query += ' AND UPPER(trait1_name)=:trait_name'

        if standardized_method1:
            query += ' AND standardized_method1=:standardized_method1'

        if standardized_method2:
            query += ' AND standardized_method2=:standardized_method2'

        return list(
            self.cursor.execute(
                query,
                {
                    'gene': gene,
                    'submitter1_id': submitter1_id,
                    'submitter2_id': submitter2_id,
                    'trait_name': trait_name,
                    'min_stars1': min_stars1,
                    'min_stars2': min_stars2,
                    'standardized_method1': standardized_method1,
                    'standardized_method2': standardized_method2,
                    'min_conflict_level': min_conflict_level,
                }
            )
        )[0][0]

    def total_variants_by_gene(self, min_stars = 0, standardized_method = None, min_conflict_level = 0):
        query = '''
            SELECT gene, COUNT(DISTINCT variant_name) AS count FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY gene ORDER BY gene'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))

    def total_variants_by_gene_and_significance(self, submitter_id = None, trait_name = None, min_stars = 0,
                                                standardized_method = None, min_conflict_level = 0,
                                                standardized_terms = False):
        query = 'SELECT gene, COUNT(DISTINCT variant_name) AS count'

        if standardized_terms:
            query += ', standardized_significance1 AS significance'
        else:
            query += ', significance1 AS significance'

        query += '''
            FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if submitter_id:
            query += ' AND submitter1_id=:submitter_id'

        if trait_name:
            query += ' AND UPPER(trait1_name)=:trait_name'

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY gene, significance ORDER BY gene, significance'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'submitter_id': submitter_id,
                    'trait_name': trait_name,
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level
                }
            )
        ))

    def total_variants_by_submitter(self, min_stars = 0, standardized_method = None, min_conflict_level = 0):
        query = '''
            SELECT
                submitter1_id AS submitter_id,
                submitter1_name AS submitter_name,
                COUNT(DISTINCT variant_name) AS count
            FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY submitter_id ORDER BY submitter_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level
                }
            )
        ))

    def total_variants_by_submitter_and_significance(self, gene = None, trait_name = None, min_stars = 0,
                                                     standardized_method = None, min_conflict_level = 0,
                                                     standardized_terms = False):
        query = '''
            SELECT
                submitter1_id AS submitter_id,
                submitter1_name AS submitter_name,
                COUNT(DISTINCT variant_name) AS count
        '''

        if standardized_terms:
            query += ', standardized_significance1 AS significance'
        else:
            query += ', significance1 AS significance'

        query += '''
            FROM current_comparisons
            WHERE
                star_level1>=:min_stars AND
                star_level2>=:min_stars AND
                conflict_level>=:min_conflict_level
        '''

        if gene:
            query += ' AND gene=:gene'

        if trait_name:
            query += ' AND UPPER(trait1_name)=:trait_name'

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY submitter_id, significance ORDER BY submitter1_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'gene': gene,
                    'trait_name': trait_name,
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level
                }
            )
        ))

    def total_variants_by_trait(self, min_stars = 0, standardized_method = None, min_conflict_level = 0):
        query = '''
            SELECT
                UPPER(trait1_name) AS trait,
                COUNT(DISTINCT variant_name) AS count
            FROM current_comparisons
            WHERE star_level1>=:min_stars AND star_level2>=:min_stars AND conflict_level>=:min_conflict_level
        '''

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY trait ORDER BY trait'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level
                }
            )
        ))

    def total_variants_by_trait_and_significance(self, gene = None, submitter_id = None, min_stars = 0,
                                                 standardized_method = None, min_conflict_level = 0, standardized_terms = False):
        query = '''
            SELECT
                trait1_db AS trait_db,
                trait1_id AS trait_id,
                UPPER(trait1_name) AS trait_name,
                COUNT(DISTINCT variant_name) AS count
        '''

        if standardized_terms:
            query += ', standardized_significance1 AS significance'
        else:
            query += ', significance1 AS significance'

        query += '''
            FROM current_comparisons
            WHERE
                star_level1>=:min_stars AND
                star_level2>=:min_stars AND
                conflict_level>=:min_conflict_level
        '''

        if gene:
            query += ' AND gene=:gene'

        if submitter_id:
            query += ' AND submitter1_id=:submitter_id'

        if standardized_method:
            query += ' AND standardized_method1=:standardized_method AND standardized_method2=:standardized_method'

        query += ' GROUP BY trait_name, significance ORDER BY trait_name'

        return list(map(
            dict,
            self.cursor.execute(
                query,
                {
                    'gene': gene,
                    'submitter_id': submitter_id,
                    'min_stars': min_stars,
                    'standardized_method': standardized_method,
                    'min_conflict_level': min_conflict_level
                }
            )
        ))

    def variant_id(self, variant_name):
        return list(self.cursor.execute(
            'SELECT variant_id FROM current_submissions WHERE variant_name=?', [variant_name]
        ))[0][0]

    def variants(self, submitter1_id = None, submitter2_id = None, significance1 = None, significance2 = None,
                 min_stars1 = 0, min_stars2 = 0, standardized_method1 = None, standardized_method2 = None,
                 min_conflict_level = 1, standardized_terms = False):
        query = '''
            SELECT DISTINCT variant_name FROM current_comparisons
            WHERE star_level1>=:min_stars1 AND star_level2>=:min_stars2 AND conflict_level>=:min_conflict_level
        '''

        if submitter1_id:
            query += ' AND submitter1_id=:submitter1_id'

        if submitter2_id:
            query += ' AND submitter2_id=:submitter2_id'

        if standardized_terms:
            if significance1:
                query += ' AND standardized_significance1=:significance1'
            if significance2:
                query += ' AND standardized_significance2=:significance2'
        else:
            if significance1:
                query += ' AND significance1=:significance1'
            if significance2:
                query += ' AND significance2=:significance2'

        if standardized_method1:
            query += ' AND standardized_method1=:standardized_method1'

        if standardized_method2:
            query += ' AND standardized_method2=:standardized_method2'

        query += ' ORDER BY variant_name'

        return list(map(
            lambda row: row[0],
            self.cursor.execute(
                query,
                {
                    'submitter1_id': submitter1_id,
                    'submitter2_id': submitter2_id,
                    'significance1': significance1,
                    'significance2': significance2,
                    'min_stars1': min_stars1,
                    'min_stars2': min_stars2,
                    'standardized_method1': standardized_method1,
                    'standardized_method2': standardized_method2,
                    'min_conflict_level': min_conflict_level,
                }
            )
        ))
