import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FLEET ANALYTICS CLASS ---
class MetroFleetAnalytics:
    def __init__(self, df):
        self.df = df.copy()

    def fleet_health_index(self):
        cert_overdue = ((self.df['rs_days_from_plan'] < 0).sum() +
                        (self.df['sig_days_from_plan'] < 0).sum() +
                        (self.df['tel_days_from_plan'] < 0).sum())
        maintenance_score = max(0, 100 - (cert_overdue * 15) - (self.df['job_critical_count'].sum() * 10))
        service_ready = (self.df['assigned_status'].isin(['Service', 'Standby'])).sum()
        availability_score = (service_ready / len(self.df)) * 100
        avg_failure_risk = self.df['predicted_failure_risk'].mean()
        avg_wear = self.df['bogie_wear_index'].mean()
        efficiency_score = max(0, 100 - (avg_failure_risk * 200) - (avg_wear * 100))
        hvac_issues = self.df['hvac_alert'].sum()
        high_temp_count = (self.df['iot_temp_avg_c'] > 30).sum()
        safety_score = max(0, 100 - (hvac_issues * 10) - (high_temp_count * 5))
        depot_std = self.df.groupby('depot').size().std()
        utilization_score = max(0, 100 - (depot_std * 10))
        score = (
            maintenance_score * 0.3 +
            availability_score * 0.25 +
            efficiency_score * 0.2 +
            safety_score * 0.15 +
            utilization_score * 0.1
        )
        return round(score, 2)

    def predictive_maintenance_alerts(self):
        alerts = []
        for _, t in self.df.iterrows():
            train_alerts = []
            if t.predicted_failure_risk > 0.25:
                train_alerts.append(("PREDICTIVE_FAILURE", "HIGH" if t.predicted_failure_risk > 0.35 else "MEDIUM", t.predicted_failure_risk))
            if t.bogie_wear_index > 0.35:
                train_alerts.append(("BOGIE_WEAR", "MEDIUM", t.bogie_wear_index))
            if t.iot_temp_avg_c > 29 and t.hvac_alert == 0:
                train_alerts.append(("TEMP_ANOMALY", "LOW", t.iot_temp_avg_c))
            if train_alerts:
                alerts.append({'train_id': t.train_id, 'depot': t.depot, 'alerts': train_alerts})
        return alerts

    def resource_optimization(self):
        optimizations = []
        depots = self.df.groupby('depot').agg(
            job_open_count=('job_open_count', 'sum'),
            job_critical_count=('job_critical_count', 'sum'),
            count=('train_id', 'count')
        )
        depots['wl_per_train'] = (depots.job_open_count + 2*depots.job_critical_count)/depots['count']
        if depots['wl_per_train'].max() > depots['wl_per_train'].min() * 1.5:
            optimizations.append("Workload imbalance detected between depots.")
        clean_cnt = (self.df['cleaning_slot'] == "No-Clean").sum()
        if clean_cnt > len(self.df)*0.4:
            optimizations.append("Cleaning slot schedule sub-optimal (many No-Cleans).")
        return optimizations

    def revenue_impact(self):
        out_service = (self.df['assigned_status'] == 'IBL').sum()
        revenue_per_km = 25
        daily_per_train = 150
        maint_cost_per_hour = 5000
        branding_shortfall = max(0, self.df.branding_req_hours.sum() - self.df.branding_alloc_hours.sum()) * 2000
        return {
            'out_of_service': int(out_service),
            'potential_loss': int(out_service * daily_per_train * revenue_per_km),
            'maint_cost_today': int(self.df.job_open_count.sum() * 4 * maint_cost_per_hour),
            'branding_shortfall_cost': int(branding_shortfall)
        }

    def dynamic_route_assignment(self):
        profile = {
            'Peak_Express': {'demand': 1.8, 'reliability': 0.9, 'mileage': 1.2},
            'Off_Peak_Local': {'demand': 0.7, 'reliability': 0.7, 'mileage': 0.8},
            'Airport_Connector': {'demand': 1.5, 'reliability': 0.95, 'mileage': 1.1},
            'Tourist_Circuit': {'demand': 1.0, 'reliability': 0.85, 'mileage': 0.9},
        }
        results = []
        for _, t in self.df.iterrows():
            if t.assigned_status == 'Service':
                reliability = 1 - t.predicted_failure_risk - (t.bogie_wear_index * 0.3)
                best = None; best_score = 0
                for route, p in profile.items():
                    if reliability >= p['reliability']:
                        score = reliability * p['demand'] * (2 - p['mileage'])
                        if score > best_score:
                            best = route; best_score = score
                results.append({'train_id': t.train_id, 'assigned_route': best or 'Maintenance_Priority', 'reliability': round(reliability,3)})
        return results

    def energy_efficiency(self):
        energy = []
        for _, t in self.df.iterrows():
            base, wc, hc, ta, sp = 100, t.bogie_wear_index * 20, t.hvac_alert * 15, max(0, (t.iot_temp_avg_c - 25) * 0.8), t.estimated_shunting_mins * 0.2
            total = base + wc + hc + ta + sp
            rating = "Excellent" if total < 110 else "Good" if total < 125 else "Poor"
            cause = "Bogie Wear" if wc > 7 else "HVAC" if hc > 10 else "Temp" if ta > 5 else "Ops"
            energy.append({'train_id': t.train_id, 'kWh/100km': round(total,1), 'rating': rating, 'main_issue': cause})
        return energy

    def passenger_experience(self):
        impacts = []
        for _, t in self.df.iterrows():
            score, factors = 100, []
            if t.hvac_alert == 1: score -= 25; factors.append("HVAC malfunction")
            if t.iot_temp_avg_c > 28: score -= 10; factors.append("High cabin temperature")
            if t.cleaning_slot == "No-Clean": score -= 15; factors.append("No cleaning scheduled")
            if t.predicted_failure_risk > 0.3: score -= 20; factors.append("High service interruption risk")
            if t.bogie_wear_index > 0.35: score -= 10; factors.append("Noise/Vibration risk")
            if t.estimated_shunting_mins > 30: score -=8; factors.append("Extended shunting delays")
            rating = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 60 else "Poor"
            impacts.append({'train_id':t.train_id, 'score':max(0,score), 'rating':rating, 'factors':factors[:2] or ["None"]})
        return impacts

    def intelligent_maintenance_schedule(self):
        schedule = {}
        for _, t in self.df.iterrows():
            prio, typ, urg = 0, [], 'LOW'
            if t.job_critical_count > 0: prio+=100; typ.append("Critical"); urg='IMMEDIATE'
            if t.rs_days_from_plan <= 5: prio+=80; typ.append("RS Cert"); urg='HIGH' if urg != 'IMMEDIATE' else urg
            if t.sig_days_from_plan <= 5: prio+=75; typ.append("SIG Check"); urg='HIGH' if urg != 'IMMEDIATE' else urg
            if t.tel_days_from_plan <= 5: prio+=70; typ.append("TEL Maint"); urg='HIGH' if urg != 'IMMEDIATE' else urg
            if t.predicted_failure_risk > 0.25: prio+=t.predicted_failure_risk*100; typ.append("Predictive"); urg='MEDIUM' if urg == 'LOW' else urg
            if t.bogie_wear_index > 0.35: prio+=t.bogie_wear_index*50; typ.append("Bogie"); urg='MEDIUM' if urg == 'LOW' else urg
            if prio > 0:
                sched = {"priority": round(prio,1), "urgency": urg, "types": typ,
                         "window": "Within 24 hours" if urg=='IMMEDIATE' else ("Within 72 hours" if urg=='HIGH' else "Next scheduled window"),
                         "est_hours": len(typ)*4 + t.job_open_count*2}
                schedule[t.train_id] = sched
        return dict(sorted(schedule.items(), key=lambda x:x[1]['priority'], reverse=True))

   # --- FIXED: FLEET ALLOCATION JUSTIFICATION ---
    def fleet_allocation_justification(self, service_start="06:00", service_end="22:30", avg_headway_minutes=7.5, revenue_per_train=150*25):
        """
        Computes the minimum trains needed in Service, Standby, and IBL based on:
        - Service hours
        - Average headway
        - Current fleet size
        Also returns potential revenue from Service trains.
        """
        start_time = datetime.strptime(service_start, "%H:%M")
        end_time = datetime.strptime(service_end, "%H:%M")
        service_minutes = (end_time - start_time).total_seconds() / 60

        fleet_size = len(self.df)

        # Minimum trains to maintain headway
        min_service_trains = int(service_minutes / avg_headway_minutes + 0.5)
        # Ensure we don't exceed fleet
        min_service_trains = min(min_service_trains, fleet_size)

        # Eligible trains left after service allocation
        remaining_trains = fleet_size - min_service_trains

        # Maximum 4 Standby trains (capped for operational efficiency)
        MAX_STANDBY_TRAINS = 4
        min_standby_trains = min(max(3, remaining_trains), MAX_STANDBY_TRAINS) if remaining_trains > 0 else 3

        # Remaining trains are IBL
        min_ibl_trains = max(0, fleet_size - (min_service_trains + min_standby_trains))

        expected_revenue = min_service_trains * revenue_per_train

        justification = {
            'fleet_size': fleet_size,
            'min_service_trains': min_service_trains,
            'min_standby_trains': min_standby_trains,
            'min_ibl_trains': min_ibl_trains,
            'expected_revenue': expected_revenue,
            'note': (
                "Service trains are calculated based on service hours and headway.\n"
                "Standby trains are capped at maximum 4 units for operational efficiency.\n"
                "IBL (In-Bay-Lockdown) are the remaining trains not in active service or standby.\n"
                "Revenue is earned only from Service trains."
            )
        }
        return justification


    # Optional: a combined report
    def generate_kmrl_report(self):
        report = {
            'Fleet Health Index': self.fleet_health_index(),
            'Predictive Maintenance Alerts': self.predictive_maintenance_alerts(),
            'Resource Optimization Suggestions': self.resource_optimization(),
            'Revenue Impact': self.revenue_impact(),
            'Dynamic Route Assignment': self.dynamic_route_assignment(),
            'Energy Efficiency': self.energy_efficiency(),
            'Passenger Experience': self.passenger_experience(),
            'Intelligent Maintenance Schedule': self.intelligent_maintenance_schedule(),
            'Fleet Allocation Justification': self.fleet_allocation_justification()
        }
        
        return report
    
    def print_fleet_report(report):
        print("\n" + "="*70)
        print("🚆  METRO FLEET ANALYTICS REPORT".center(70))
        print("="*70 + "\n")

        # Fleet Health Index
        print("🔹 FLEET HEALTH INDEX".ljust(40))
        print(f"   Score: {report['Fleet Health Index']}\n")

        # Predictive Maintenance Alerts
        print("🔹 PREDICTIVE MAINTENANCE ALERTS".ljust(40))
        if report['Predictive Maintenance Alerts']:
            for alert in report['Predictive Maintenance Alerts']:
                print(f"   Train {alert['train_id']} ({alert['depot']}):")
                for a_type, severity, val in alert['alerts']:
                    print(f"      • {a_type} | Severity: {severity} | Value: {val}")
        else:
            print("   No critical alerts.")
        print()

        # Resource Optimization
        print("🔹 RESOURCE OPTIMIZATION SUGGESTIONS")
        if report['Resource Optimization Suggestions']:
            for suggestion in report['Resource Optimization Suggestions']:
                print(f"   • {suggestion}")
        else:
            print("   All depots optimized.")
        print()

        # Revenue Impact
        revenue = report['Revenue Impact']
        print("🔹 REVENUE IMPACT")
        print(f"   Out-of-Service Trains: {revenue['out_of_service']}")
        print(f"   Potential Revenue Loss: ₹{revenue['potential_loss']}")
        print(f"   Maintenance Cost Today: ₹{revenue['maint_cost_today']}")
        print(f"   Branding Shortfall Cost: ₹{revenue['branding_shortfall_cost']}\n")

        # Dynamic Route Assignment
        print("🔹 DYNAMIC ROUTE ASSIGNMENT")
        for route in report['Dynamic Route Assignment']:
            print(f"   Train {route['train_id']} → Route: {route['assigned_route']}, Reliability: {route['reliability']}")
        print()

        # Energy Efficiency
        print("🔹 ENERGY EFFICIENCY")
        for e in report['Energy Efficiency']:
            print(f"   Train {e['train_id']} → {e['kWh/100km']} kWh | Rating: {e['rating']} | Main Issue: {e['main_issue']}")
        print()

        # Passenger Experience
        print("🔹 PASSENGER EXPERIENCE")
        for p in report['Passenger Experience']:
            factors = ", ".join(p['factors'])
            print(f"   Train {p['train_id']} → Score: {p['score']} | Rating: {p['rating']} | Factors: {factors}")
        print()

        # Intelligent Maintenance Schedule
        print("🔹 INTELLIGENT MAINTENANCE SCHEDULE")
        for tid, sched in report['Intelligent Maintenance Schedule'].items():
            types = ", ".join(sched['types'])
            print(f"   Train {tid} → Priority: {sched['priority']} | Urgency: {sched['urgency']} | Types: {types} | Est. Hours: {sched['est_hours']}")
        print()

        # Fleet Allocation Justification
        fa = report['Fleet Allocation Justification']
        print("🔹 FLEET ALLOCATION JUSTIFICATION")
        print(f"   Total Fleet Size: {fa['fleet_size']}")
        print(f"   Minimum Service (Revenue) Trains: {fa['min_service_trains']}")
        print(f"   Minimum Standby Trains: {fa['min_standby_trains']}")
        print(f"   Minimum IBL Trains: {fa['min_ibl_trains']}")
        print(f"   Note: {fa['note']}")
        print("\n" + "="*70 + "\n")

    
