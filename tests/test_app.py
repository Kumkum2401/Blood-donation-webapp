import os
import tempfile
import unittest

from app import create_app, init_db


class BloodDonationAppTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "DATABASE": self.db_path,
            }
        )
        init_db(self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Blood Donation Web App", response.data)

    def test_register_donor(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Anita",
                "age": "24",
                "blood_group": "O+",
                "contact": "9999999999",
                "city": "Delhi",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Donor registered successfully!", response.data)

    def test_submit_emergency_request(self):
        response = self.client.post(
            "/emergency",
            data={
                "patient_name": "Ravi",
                "blood_group": "A+",
                "units_needed": "2 units",
                "hospital": "City Hospital",
                "contact": "8888888888",
                "message": "Urgent requirement",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Emergency request submitted successfully.", response.data)


if __name__ == "__main__":
    unittest.main()
