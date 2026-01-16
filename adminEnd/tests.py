from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminEndSmokeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(email='admin@example.com', password='pass', full_name='Admin', role=User.Role.ADMIN, is_staff=True)
        self.student_user = User.objects.create_user(email='student@example.com', password='pass', full_name='Student', role=User.Role.STUDENT)

    def test_dashboard_requires_admin(self):
        # Anonymous should be redirected to login (home)
        r = self.client.get(reverse('adminEnd:dashboard'))
        self.assertIn(r.status_code, (302, 302))

        # Student should be denied (redirect)
        self.client.login(email='student@example.com', password='pass')
        r = self.client.get(reverse('adminEnd:dashboard'))
        self.assertIn(r.status_code, (302, 302))

        # Admin can access
        self.client.login(email='admin@example.com', password='pass')
        r = self.client.get(reverse('adminEnd:dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_incident_list_page_for_admin(self):
        self.client.login(email='admin@example.com', password='pass')
        r = self.client.get(reverse('adminEnd:incident_list'))
        self.assertEqual(r.status_code, 200)

    def test_assign_unassign_flow(self):
        from incidents.models import Beacon, Incident
        from security.models import GuardProfile, GuardAssignment

        # Create beacon and incident
        beacon = Beacon.objects.create(beacon_id='test-beacon-1', uuid='uuid', major=1, minor=1, location_name='Test Hall', building='Main', floor=1, is_active=True)
        incident = Incident.objects.create(beacon=beacon)

        # Create guard user and profile
        guard = User.objects.create_user(email='guard@example.com', password='pass', full_name='Guard', role=User.Role.GUARD)
        GuardProfile.objects.create(user=guard, is_active=True, is_available=True)

        self.client.login(email='admin@example.com', password='pass')
        detail_url = reverse('adminEnd:incident_detail', kwargs={'incident_id': incident.id})

        # Assign guard
        r = self.client.post(detail_url, {'assign': '1', 'guard_id': str(guard.id)})
        self.assertEqual(r.status_code, 302)

        # Verify assignment
        assignment = GuardAssignment.objects.filter(incident=incident, guard=guard).first()
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_active)
        incident.refresh_from_db()
        self.assertEqual(incident.current_assigned_guard, guard)
        self.assertEqual(incident.status, Incident.Status.ASSIGNED)

        # Unassign
        r = self.client.post(detail_url, {'unassign': '1'})
        self.assertEqual(r.status_code, 302)

        assignment.refresh_from_db()
        incident.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertIsNone(incident.current_assigned_guard)
        self.assertEqual(incident.status, Incident.Status.CREATED)

    def test_beacon_create_edit(self):
        from incidents.models import Beacon
        self.client.login(email='admin@example.com', password='pass')
        create_url = reverse('adminEnd:beacon_create')
        r = self.client.post(create_url, {
            'beacon_id': 'b-100', 'uuid': 'u-100', 'major': 1, 'minor': 1, 'location_name': 'Hall 1', 'building': 'Main', 'floor': 1, 'is_active': True
        })
        # Should redirect to detail
        self.assertEqual(r.status_code, 302)
        beacon = Beacon.objects.get(beacon_id='b-100')
        self.assertEqual(beacon.location_name, 'Hall 1')

        # Edit beacon
        detail_url = reverse('adminEnd:beacon_detail', kwargs={'beacon_id': beacon.id})
        r = self.client.post(detail_url, {'location_name': 'Hall 1A'})
        self.assertEqual(r.status_code, 302)
        beacon.refresh_from_db()
        self.assertEqual(beacon.location_name, 'Hall 1A')

    def test_guard_toggle_availability(self):
        from django.contrib.auth import get_user_model
        from security.models import GuardProfile

        # Create guard
        guard = User.objects.create_user(email='g2@example.com', password='pass', full_name='Guard2', role=User.Role.GUARD)
        GuardProfile.objects.create(user=guard, is_active=True, is_available=True)

        self.client.login(email='admin@example.com', password='pass')
        r = self.client.post(reverse('adminEnd:toggle_guard_availability', kwargs={'user_id': guard.id}))
        self.assertEqual(r.status_code, 302)
        guard.refresh_from_db()
        self.assertFalse(guard.guard_profile.is_available)

    def test_beacon_proximity_add_delete(self):
        from incidents.models import Beacon, BeaconProximity

        self.client.login(email='admin@example.com', password='pass')

        b1 = Beacon.objects.create(beacon_id='p-b1', uuid='u1', major=1, minor=1, location_name='B1', building='Main', floor=1, is_active=True)
        b2 = Beacon.objects.create(beacon_id='p-b2', uuid='u2', major=2, minor=2, location_name='B2', building='Main', floor=1, is_active=True)

        detail_url = reverse('adminEnd:beacon_detail', kwargs={'beacon_id': b1.id})

        # Add proximity b1 -> b2
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b2.id), 'priority': 1})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(BeaconProximity.objects.filter(from_beacon=b1, to_beacon=b2).exists())

        # Prevent self reference
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b1.id), 'priority': 1})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(BeaconProximity.objects.filter(from_beacon=b1, to_beacon=b1).exists())

        # Duplicate prevention
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b2.id), 'priority': 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(BeaconProximity.objects.filter(from_beacon=b1, to_beacon=b2).count(), 1)

        # Add again with priority 1 and ensure existing shifts to priority 2
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b2.id), 'priority': 1})
        # Should return 200 with error (duplicate) because relation exists
        self.assertEqual(r.status_code, 200)

        # Remove and re-add to test shifting
        prox = BeaconProximity.objects.get(from_beacon=b1, to_beacon=b2)
        r = self.client.post(detail_url, {'delete_proximity': '1', 'proximity_id': prox.id})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(BeaconProximity.objects.filter(id=prox.id).exists())

        # Add b2 at priority 2
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b2.id), 'priority': 2})
        self.assertEqual(r.status_code, 302)
        prox = BeaconProximity.objects.get(from_beacon=b1, to_beacon=b2)
        self.assertEqual(prox.priority, 2)

        # Add b3 at priority 2 and ensure b2 moves to 3
        b3 = Beacon.objects.create(beacon_id='p-b3', uuid='u3', major=3, minor=3, location_name='B3', building='Main', floor=2, is_active=True)
        r = self.client.post(detail_url, {'add_proximity': '1', 'to_beacon': str(b3.id), 'priority': 2})
        self.assertEqual(r.status_code, 302)
        b2p = BeaconProximity.objects.get(from_beacon=b1, to_beacon=b2)
        b3p = BeaconProximity.objects.get(from_beacon=b1, to_beacon=b3)
        self.assertEqual(b3p.priority, 2)
        self.assertEqual(b2p.priority, 3)

        # Test move up/down via AJAX endpoints
        move_url = reverse('adminEnd:ajax_move_proximity', kwargs={'beacon_id': b1.id, 'prox_id': b2p.id})
        r = self.client.post(move_url, {'direction': 'up'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('success'))
        b2p.refresh_from_db(); b3p.refresh_from_db()
        self.assertEqual(b2p.priority, 2)
        self.assertEqual(b3p.priority, 3)

        r = self.client.post(move_url.replace(str(b2p.id), str(b2p.id)), {'direction': 'down'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('success'))
        b2p.refresh_from_db(); b3p.refresh_from_db()
        self.assertEqual(b2p.priority, 3)
        self.assertEqual(b3p.priority, 2)

        # Test update priority via AJAX
        upd_url = reverse('adminEnd:ajax_update_proximity_priority', kwargs={'beacon_id': b1.id, 'prox_id': b3p.id})
        r = self.client.post(upd_url, {'priority': 1})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('success'))
        b3p.refresh_from_db(); b2p.refresh_from_db()
        self.assertEqual(b3p.priority, 1)

        # Delete proximity via AJAX
        del_url = reverse('adminEnd:ajax_delete_proximity', kwargs={'beacon_id': b1.id, 'prox_id': b2p.id})
        r = self.client.post(del_url)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get('success'))
        self.assertFalse(BeaconProximity.objects.filter(id=b2p.id).exists())
        # Delete proximity
        prox = BeaconProximity.objects.get(from_beacon=b1, to_beacon=b2)
        r = self.client.post(detail_url, {'delete_proximity': '1', 'proximity_id': prox.id})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(BeaconProximity.objects.filter(id=prox.id).exists())
